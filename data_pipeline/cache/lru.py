"""
Thread-safe namespaced LRU cache with TTL, capacity, request-coalescing (in-progress futures)
and basic metrics. Designed for storing primary parsing results and secondary artifacts.
"""
from __future__ import annotations

import threading
import time
from collections import OrderedDict
from concurrent.futures import Future
from typing import Any, Callable, Dict, Optional, Tuple


class CacheEntry:
    def __init__(self, value: Any, expires_at: Optional[float]):
        self.value = value
        self.expires_at = expires_at


class NamespacedLRU:
    """A simple in-memory namespaced LRU cache.

    - Namespaces isolate keys (prevents cross-View pollution).
    - Keys should be structured strings (server resolves endpointId).
    - Thread-safe with a reentrant lock.
    - Request coalescing: identical-key concurrent computations run once.
    - TTL support and eviction reasons counting.
    - Exposes simple metrics: hits/misses/evictions/in_progress_count.
    """

    def __init__(self, capacity: int = 1024, default_ttl: Optional[int] = 300):
        self.capacity = max(1, int(capacity))
        self.default_ttl = default_ttl
        self._namespaces: Dict[str, OrderedDict[str, CacheEntry]] = {}
        self._locks: Dict[str, threading.RLock] = {}
        self._global_lock = threading.RLock()
        self._in_progress: Dict[Tuple[str, str], Future] = {}
        # metrics
        self.metrics = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "expired": 0,
            "coalesced": 0,
        }

    def _get_ns_store(self, namespace: str) -> OrderedDict:
        with self._global_lock:
            if namespace not in self._namespaces:
                self._namespaces[namespace] = OrderedDict()
                self._locks[namespace] = threading.RLock()
            return self._namespaces[namespace]

    def _now(self) -> float:
        return time.time()

    def _is_expired(self, entry: CacheEntry) -> bool:
        return entry.expires_at is not None and entry.expires_at < self._now()

    def _evict_if_needed(self, namespace: str):
        store = self._get_ns_store(namespace)
        while len(store) > self.capacity:
            k, _ = store.popitem(last=False)
            self.metrics["evictions"] += 1

    def make_key(self, *, module: str, endpoint_id: str, request_type: str, config_version: str,
                 time_start: str, time_end: str, time_step: int, train_no: str, carriage: str, parse_mode: str) -> str:
        """Return a deterministic structured key string. All components should be canonicalized by caller."""
        parts = [module, endpoint_id, request_type, f"cfg={config_version}", f"ts={time_start}", f"te={time_end}",
                 f"step={time_step}", f"train={train_no}", f"carriage={carriage}", f"mode={parse_mode}"]
        return "|".join(parts)

    def get(self, namespace: str, key: str) -> Optional[Any]:
        store = self._get_ns_store(namespace)
        lock = self._locks[namespace]
        with lock:
            entry = store.get(key)
            if entry is None:
                self.metrics["misses"] += 1
                return None
            if self._is_expired(entry):
                # expired
                del store[key]
                self.metrics["expired"] += 1
                self.metrics["misses"] += 1
                return None
            # mark as recently used
            store.move_to_end(key)
            self.metrics["hits"] += 1
            return entry.value

    def set(self, namespace: str, key: str, value: Any, ttl: Optional[int] = None) -> None:
        store = self._get_ns_store(namespace)
        lock = self._locks[namespace]
        with lock:
            expires_at = None
            ttl = self.default_ttl if ttl is None else ttl
            if ttl is not None and ttl > 0:
                expires_at = self._now() + ttl
            store[key] = CacheEntry(value, expires_at)
            store.move_to_end(key)
            self._evict_if_needed(namespace)

    def get_or_compute(self, namespace: str, key: str, factory: Callable[[], Any], ttl: Optional[int] = None) -> Any:
        """Atomic get-or-compute with request coalescing. If a computation for the same key is in progress,
        callers will wait for the single in-flight result.
        """
        # Fast path: check existing
        val = self.get(namespace, key)
        if val is not None:
            return val

        marker = (namespace, key)
        with self._global_lock:
            future = self._in_progress.get(marker)
            if future is None:
                # create a new future and start computing
                future = Future()
                self._in_progress[marker] = future
            else:
                # someone else is computing
                self.metrics["coalesced"] += 1
        if future.done():
            # race: it finished between checks
            res = future.result()
            return res

        # If this thread created the future, compute; otherwise wait
        created = future.running() is False and future.done() is False and future not in ()
        # Use try/except to ensure future is completed and cleaned up
        is_computer = False
        with self._global_lock:
            if not future.done() and not getattr(future, "_started_by_us", False):
                # mark that we will compute
                future._started_by_us = True
                is_computer = True
        if is_computer:
            try:
                result = factory()
                # store in cache
                self.set(namespace, key, result, ttl=ttl)
                future.set_result(result)
            except Exception as exc:
                future.set_exception(exc)
                raise
            finally:
                with self._global_lock:
                    self._in_progress.pop(marker, None)
            return result
        else:
            # wait for the computing thread
            try:
                result = future.result()
                # cached value should now be present; return it
                return result
            except Exception:
                # propagate
                raise

    def inspect_namespace(self, namespace: str) -> Dict[str, Any]:
        store = self._get_ns_store(namespace)
        lock = self._locks[namespace]
        with lock:
            keys = list(store.keys())
            size = len(store)
        return {
            "namespace": namespace,
            "size": size,
            "keys_sample": keys[:20],
            "metrics": dict(self.metrics),
            "in_progress": len([k for k in self._in_progress if k[0] == namespace]),
        }

    def clear_namespace(self, namespace: str):
        with self._global_lock:
            if namespace in self._namespaces:
                self._namespaces[namespace].clear()
                self.metrics["evictions"] += 1

    def clear_all(self):
        with self._global_lock:
            for ns in list(self._namespaces.keys()):
                self._namespaces[ns].clear()
            self.metrics = {k: 0 for k in self.metrics}

