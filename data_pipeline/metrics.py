"""
Metrics collection and reporting for cache and pipeline operations.
Tracks hit/miss/eviction rates, hot keys, and namespace statistics.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
from datetime import datetime
import threading
import json


@dataclass
class CacheMetrics:
    """Metrics for cache operations."""
    total_hits: int = 0
    total_misses: int = 0
    total_evictions: int = 0
    total_sets: int = 0
    
    # Namespace-specific metrics
    namespace_hits: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    namespace_misses: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    namespace_evictions: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    
    # Hot key tracking (top-N most accessed keys)
    key_access_counts: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    
    # Eviction reason tracking
    eviction_reasons: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    
    # TTL-related stats
    ttl_expired: int = 0
    stale_hits: int = 0
    
    lock: threading.Lock = field(default_factory=threading.Lock)
    last_reset: datetime = field(default_factory=datetime.utcnow)
    
    def record_hit(self, key: str, namespace: str) -> None:
        """Record a cache hit."""
        with self.lock:
            self.total_hits += 1
            self.namespace_hits[namespace] = self.namespace_hits.get(namespace, 0) + 1
            self.key_access_counts[key] = self.key_access_counts.get(key, 0) + 1
    
    def record_miss(self, key: str, namespace: str) -> None:
        """Record a cache miss."""
        with self.lock:
            self.total_misses += 1
            self.namespace_misses[namespace] = self.namespace_misses.get(namespace, 0) + 1
            self.key_access_counts[key] = self.key_access_counts.get(key, 0) + 1
    
    def record_eviction(self, key: str, namespace: str, reason: str = "LRU") -> None:
        """Record a cache eviction."""
        with self.lock:
            self.total_evictions += 1
            self.namespace_evictions[namespace] = self.namespace_evictions.get(namespace, 0) + 1
            self.eviction_reasons[reason] = self.eviction_reasons.get(reason, 0) + 1
    
    def record_ttl_expiry(self, key: str) -> None:
        """Record TTL expiration."""
        with self.lock:
            self.ttl_expired += 1
    
    def record_stale_hit(self) -> None:
        """Record when stale data was hit (should not happen)."""
        with self.lock:
            self.stale_hits += 1
    
    def get_hit_rate(self) -> float:
        """Calculate overall hit rate (0.0-1.0)."""
        total = self.total_hits + self.total_misses
        return self.total_hits / total if total > 0 else 0.0
    
    def get_namespace_hit_rate(self, namespace: str) -> float:
        """Calculate hit rate for a specific namespace."""
        hits = self.namespace_hits.get(namespace, 0)
        misses = self.namespace_misses.get(namespace, 0)
        total = hits + misses
        return hits / total if total > 0 else 0.0
    
    def get_top_keys(self, n: int = 10) -> List[Tuple[str, int]]:
        """Get top N most accessed keys."""
        with self.lock:
            sorted_keys = sorted(
                self.key_access_counts.items(),
                key=lambda x: x[1],
                reverse=True,
            )
        return sorted_keys[:n]
    
    def get_eviction_distribution(self) -> Dict[str, int]:
        """Get distribution of eviction reasons."""
        with self.lock:
            return dict(self.eviction_reasons)
    
    def reset(self) -> None:
        """Reset all metrics."""
        with self.lock:
            self.total_hits = 0
            self.total_misses = 0
            self.total_evictions = 0
            self.total_sets = 0
            self.namespace_hits.clear()
            self.namespace_misses.clear()
            self.namespace_evictions.clear()
            self.key_access_counts.clear()
            self.eviction_reasons.clear()
            self.ttl_expired = 0
            self.stale_hits = 0
            self.last_reset = datetime.utcnow()
    
    def to_dict(self) -> Dict:
        """Convert metrics to dictionary for JSON serialization."""
        with self.lock:
            return {
                "total_hits": self.total_hits,
                "total_misses": self.total_misses,
                "total_evictions": self.total_evictions,
                "total_sets": self.total_sets,
                "hit_rate": self.get_hit_rate(),
                "ttl_expired": self.ttl_expired,
                "stale_hits": self.stale_hits,
                "namespace_hit_rates": {
                    ns: self.get_namespace_hit_rate(ns)
                    for ns in set(self.namespace_hits.keys()) | set(self.namespace_misses.keys())
                },
                "top_10_keys": dict(self.get_top_keys(10)),
                "eviction_distribution": dict(self.eviction_reasons),
                "last_reset": self.last_reset.isoformat(),
            }
    
    def __str__(self) -> str:
        """Human-readable metrics summary."""
        hit_rate = self.get_hit_rate()
        return (
            f"Cache Metrics: hits={self.total_hits}, misses={self.total_misses}, "
            f"evictions={self.total_evictions}, hit_rate={hit_rate:.2%}, "
            f"ttl_expired={self.ttl_expired}"
        )


@dataclass
class PerformanceMetrics:
    """Performance metrics for operations."""
    operation_timings: Dict[str, List[float]] = field(default_factory=lambda: defaultdict(list))
    lock: threading.Lock = field(default_factory=threading.Lock)
    
    def record_operation(self, operation: str, duration_ms: float) -> None:
        """Record an operation's duration in milliseconds."""
        with self.lock:
            self.operation_timings[operation].append(duration_ms)
    
    def get_average_time(self, operation: str) -> float:
        """Get average duration for an operation."""
        with self.lock:
            times = self.operation_timings.get(operation, [])
        return sum(times) / len(times) if times else 0.0
    
    def get_percentile(self, operation: str, percentile: float = 95.0) -> float:
        """Get percentile time for an operation."""
        with self.lock:
            times = sorted(self.operation_timings.get(operation, []))
        if not times:
            return 0.0
        idx = int(len(times) * percentile / 100.0)
        return times[min(idx, len(times) - 1)]
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        result = {}
        with self.lock:
            for op, times in self.operation_timings.items():
                if times:
                    result[op] = {
                        "count": len(times),
                        "avg_ms": sum(times) / len(times),
                        "min_ms": min(times),
                        "max_ms": max(times),
                        "p95_ms": self.get_percentile(op, 95.0),
                        "p99_ms": self.get_percentile(op, 99.0),
                    }
        return result


class MetricsCollector:
    """Central metrics collector for the system."""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self.cache_metrics = CacheMetrics()
        self.perf_metrics = PerformanceMetrics()
        self._initialized = True
    
    @staticmethod
    def get_instance() -> 'MetricsCollector':
        """Get singleton instance."""
        return MetricsCollector()
    
    def to_dict(self) -> Dict:
        """Export all metrics."""
        return {
            "cache": self.cache_metrics.to_dict(),
            "performance": self.perf_metrics.to_dict(),
        }
    
    def __str__(self) -> str:
        return str(self.cache_metrics)
