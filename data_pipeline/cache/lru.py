"""
Advanced LRU cache with namespaces, TTL, concurrency safety, and metrics.
"""

from typing import Any, Dict, Optional, Callable, Tuple
from datetime import datetime, timedelta
import threading
from collections import OrderedDict
import hashlib
import json
from dataclasses import dataclass

from ..logging_utils import get_context_logger
from ..metrics import MetricsCollector
from ..errors import CacheError

logger = get_context_logger(__name__)


@dataclass
class CacheEntry:
    """A single cache entry with metadata."""
    value: Any
    created_at: datetime
    accessed_at: datetime
    ttl_seconds: Optional[int] = None
    namespace: str = "default"
    hits: int = 0
    
    def is_expired(self) -> bool:
        """Check if entry has expired based on TTL."""
        if self.ttl_seconds is None:
            return False
        age_seconds = (datetime.utcnow() - self.created_at).total_seconds()
        return age_seconds > self.ttl_seconds
    
    def touch(self) -> None:
        """Update access time (marks as recently used)."""
        self.accessed_at = datetime.utcnow()
        self.hits += 1


class NamespacedLRUCache:
    """
    Thread-safe LRU cache with namespace isolation, TTL support, and structured metrics.
    
    Key features:
    - Structured cache keys: module/endpointId/requestType/configVersion/...
    - Namespace isolation: prevents cross-module/interface pollution
    - TTL support: automatic expiration of old entries
    - Concurrency safety: atomic operations, read/write locks
    - Request coalescing: identical keys compute once, others await result
    - Comprehensive metrics: hit/miss/eviction tracking
    """
    
    def __init__(self, max_size: int = 1000, default_ttl_seconds: Optional[int] = 3600):
        """
        Initialize LRU cache.
        
        Args:
            max_size: Maximum number of entries across all namespaces
            default_ttl_seconds: Default TTL for entries (None = no expiration)
        """
        self.max_size = max_size
        self.default_ttl_seconds = default_ttl_seconds
        
        # Storage: namespace -> key -> CacheEntry
        self._cache: Dict[str, OrderedDict] = {}
        self._namespace_sizes: Dict[str, int] = {}
        
        # Concurrency control
        self._global_lock = threading.RLock()  # For overall structure
        self._operation_locks: Dict[str, threading.Lock] = {}  # Per-namespace locks
        
        # Request coalescing: key -> Future/Result
        self._pending_operations: Dict[str, Tuple[threading.Event, Any, Optional[Exception]]] = {}
        
        # Metrics
        self.metrics = MetricsCollector.get_instance()
    
    def _get_namespace_lock(self, namespace: str) -> threading.Lock:
        """Get or create lock for a namespace."""
        with self._global_lock:
            if namespace not in self._operation_locks:
                self._operation_locks[namespace] = threading.Lock()
            return self._operation_locks[namespace]
    
    def _build_key(
        self,
        module: str,
        endpoint_id: str,
        request_type: str,
        config_version: str,
        time_start: str,
        time_end: str,
        time_step: str,
        train_no: str,
        carriage: str,
        parse_mode: str = "standard",
    ) -> str:
        """
        Build a structured, semantic cache key from request dimensions.
        
        This ensures no pollution across different modules, endpoints, or configurations.
        """
        key_parts = [
            module,
            endpoint_id,
            request_type,
            config_version,
            time_start,
            time_end,
            time_step,
            train_no,
            carriage,
            parse_mode,
        ]
        
        key_str = "/".join(key_parts)
        # Hash for shorter representation while maintaining uniqueness
        key_hash = hashlib.sha256(key_str.encode()).hexdigest()[:16]
        return f"{module}:{endpoint_id}:{request_type}#{key_hash}"
    
    def get(self, namespace: str, key: str) -> Optional[Any]:
        """
        Get a value from cache.
        
        Returns None if not found, expired, or on error.
        """
        namespace_lock = self._get_namespace_lock(namespace)
        
        with namespace_lock:
            with self._global_lock:
                if namespace not in self._cache:
                    self.metrics.cache_metrics.record_miss(key, namespace)
                    return None
                
                cache_dict = self._cache[namespace]
                if key not in cache_dict:
                    self.metrics.cache_metrics.record_miss(key, namespace)
                    return None
            
            entry = cache_dict[key]
            
            # Check expiration
            if entry.is_expired():
                with self._global_lock:
                    del cache_dict[key]
                self.metrics.cache_metrics.record_ttl_expiry(key)
                self.metrics.cache_metrics.record_miss(key, namespace)
                logger.info(f"Cache entry expired: {key}")
                return None
            
            # Mark as recently used (move to end in OrderedDict)
            cache_dict.move_to_end(key)
            entry.touch()
            
            self.metrics.cache_metrics.record_hit(key, namespace)
            logger.debug(f"Cache hit for {key} in namespace {namespace}")
            return entry.value
    
    def set(
        self,
        namespace: str,
        key: str,
        value: Any,
        ttl_seconds: Optional[int] = None,
    ) -> None:
        """
        Set a value in cache.
        
        Args:
            namespace: Namespace to isolate this value
            key: Cache key
            value: Value to cache
            ttl_seconds: Override default TTL for this entry
        """
        namespace_lock = self._get_namespace_lock(namespace)
        ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl_seconds
        
        with namespace_lock:
            with self._global_lock:
                # Initialize namespace if needed
                if namespace not in self._cache:
                    self._cache[namespace] = OrderedDict()
                    self._namespace_sizes[namespace] = 0
                
                cache_dict = self._cache[namespace]
                total_size = sum(self._namespace_sizes.values())
                
                # Evict if necessary
                while total_size >= self.max_size and (namespace not in cache_dict or key not in cache_dict):
                    self._evict_lru_entry()
                    total_size = sum(self._namespace_sizes.values())
            
            # Create entry
            now = datetime.utcnow()
            entry = CacheEntry(
                value=value,
                created_at=now,
                accessed_at=now,
                ttl_seconds=ttl,
                namespace=namespace,
            )
            
            with self._global_lock:
                cache_dict = self._cache[namespace]
                if key in cache_dict:
                    # Update existing entry
                    cache_dict[key] = entry
                    cache_dict.move_to_end(key)
                else:
                    # Add new entry
                    cache_dict[key] = entry
                    self._namespace_sizes[namespace] = self._namespace_sizes.get(namespace, 0) + 1
            
            self.metrics.cache_metrics.total_sets += 1
            logger.debug(f"Cache set for {key} in namespace {namespace}, ttl={ttl}s")
    
    def _evict_lru_entry(self) -> None:
        """Evict the least recently used entry from the oldest namespace."""
        # Find the oldest accessed entry across all namespaces
        oldest_key = None
        oldest_entry = None
        oldest_namespace = None
        oldest_time = datetime.utcnow()
        
        for namespace, cache_dict in self._cache.items():
            if cache_dict:
                # Get first (oldest) entry in OrderedDict
                first_key = next(iter(cache_dict))
                first_entry = cache_dict[first_key]
                
                if first_entry.accessed_at < oldest_time:
                    oldest_time = first_entry.accessed_at
                    oldest_key = first_key
                    oldest_entry = first_entry
                    oldest_namespace = namespace
        
        if oldest_key and oldest_namespace:
            del self._cache[oldest_namespace][oldest_key]
            self._namespace_sizes[oldest_namespace] -= 1
            self.metrics.cache_metrics.record_eviction(oldest_key, oldest_namespace, "LRU")
            logger.info(f"Evicted LRU entry {oldest_key} from namespace {oldest_namespace}")
    
    def delete(self, namespace: str, key: str) -> bool:
        """Delete a cache entry. Returns True if deleted, False if not found."""
        namespace_lock = self._get_namespace_lock(namespace)
        
        with namespace_lock:
            with self._global_lock:
                if namespace not in self._cache or key not in self._cache[namespace]:
                    return False
                
                del self._cache[namespace][key]
                self._namespace_sizes[namespace] -= 1
                logger.info(f"Deleted cache entry {key} from namespace {namespace}")
                return True
    
    def clear_namespace(self, namespace: str) -> int:
        """Clear all entries in a namespace. Returns count of cleared entries."""
        namespace_lock = self._get_namespace_lock(namespace)
        
        with namespace_lock:
            with self._global_lock:
                if namespace not in self._cache:
                    return 0
                
                count = len(self._cache[namespace])
                self._cache[namespace].clear()
                self._namespace_sizes[namespace] = 0
                logger.info(f"Cleared namespace {namespace}, removed {count} entries")
                return count
    
    def clear_all(self) -> int:
        """Clear entire cache. Returns total count of cleared entries."""
        with self._global_lock:
            total = sum(len(cache_dict) for cache_dict in self._cache.values())
            self._cache.clear()
            self._namespace_sizes.clear()
            logger.info(f"Cleared entire cache, removed {total} entries")
            return total
    
    def get_namespace_size(self, namespace: str) -> int:
        """Get number of entries in a namespace."""
        with self._global_lock:
            return self._namespace_sizes.get(namespace, 0)
    
    def get_total_size(self) -> int:
        """Get total number of entries across all namespaces."""
        with self._global_lock:
            return sum(self._namespace_sizes.values())
    
    def get_namespaces(self) -> list:
        """Get list of all namespaces."""
        with self._global_lock:
            return list(self._cache.keys())
    
    def get_keys(self, namespace: str) -> list:
        """Get all keys in a namespace."""
        with self._global_lock:
            if namespace not in self._cache:
                return []
            return list(self._cache[namespace].keys())
    
    def prewarm(
        self,
        namespace: str,
        keys_and_values: Dict[str, Any],
        ttl_seconds: Optional[int] = None,
    ) -> int:
        """
        Prewarm cache with multiple entries.
        
        Returns count of entries added.
        """
        count = 0
        for key, value in keys_and_values.items():
            self.set(namespace, key, value, ttl_seconds)
            count += 1
        logger.info(f"Prewarmed namespace {namespace} with {count} entries")
        return count
    
    def compute_once(
        self,
        namespace: str,
        key: str,
        compute_fn: Callable[[], Any],
        ttl_seconds: Optional[int] = None,
    ) -> Any:
        """
        Compute a value once, with request coalescing.
        
        If multiple threads request the same key simultaneously, only one executes
        compute_fn; others wait for the result.
        """
        # Quick check if already cached
        cached = self.get(namespace, key)
        if cached is not None:
            return cached

        # Request coalescing with single-owner computation
        full_key = f"{namespace}:{key}"
        is_owner = False
        
        with self._global_lock:
            if full_key in self._pending_operations:
                event, result, exception = self._pending_operations[full_key]
            else:
                # First requester becomes the owner responsible for computation
                event = threading.Event()
                self._pending_operations[full_key] = (event, None, None)
                is_owner = True

        if not is_owner:
            # Wait for owner to finish computation
            event.wait()
            _, result, exception = self._pending_operations[full_key]
            if exception:
                raise exception
            return result

        # Owner computes the value
        try:
            result = compute_fn()
            self.set(namespace, key, result, ttl_seconds)

            with self._global_lock:
                self._pending_operations[full_key] = (event, result, None)

            event.set()
            logger.debug(f"Computed and cached {key} in namespace {namespace}")
            return result

        except Exception as e:
            with self._global_lock:
                self._pending_operations[full_key] = (event, None, e)
            event.set()
            logger.error(f"Computation failed for {key}: {str(e)}")
            raise


class CacheKeyBuilder:
    """Helper to build structured cache keys."""
    
    @staticmethod
    def build_key(
        module: str,
        endpoint_id: str,
        request_type: str,
        config_version: str,
        time_start: str,
        time_end: str,
        time_step: str,
        train_no: str,
        carriage: str,
        parse_mode: str = "standard",
    ) -> str:
        """Build a structured cache key."""
        cache = NamespacedLRUCache()
        return cache._build_key(
            module, endpoint_id, request_type, config_version,
            time_start, time_end, time_step, train_no, carriage, parse_mode,
        )
