"""Namespaced, TTL-aware, concurrency-safe LRU cache with request coalescing and metrics hooks.

Design goals (minimal, testable):
- structured keys (caller composes namespace + semantic key)
- per-namespace ops (invalidate, inspect)
- TTL and capacity-based eviction with reason logging
- request coalescing: identical-key compute runs once (other callers wait)
- metrics callbacks (increment counters)
"""
from __future__ import annotations

import time
import threading
from collections import OrderedDict
from typing import Any, Callable, Dict, Optional, Tuple
import concurrent.futures

from .. import metrics as _metrics
from ..errors import CacheError


class CacheEntry:
    __slots__ = ("value", "expiry", "created_at")

    def __init__(self, value: Any, ttl: Optional[float]):
        self.value = value
        self.created_at = time.time()
        self.expiry = (self.created_at + ttl) if ttl and ttl > 0 else None

    def is_expired(self) -> bool:
        return self.expiry is not None and time.time() > self.expiry


class NamespacedLRUCache:
    def __init__(self, capacity: int = 1024, default_ttl: Optional[float] = 300, namespace: str = "default"):
        self.capacity = int(capacity)
        self.default_ttl = default_ttl
        self.namespace = namespace

        self._lock = threading.RLock()
        self._data: "OrderedDict[str, CacheEntry]" = OrderedDict()
        self._in_flight: Dict[str, concurrent.futures.Future] = {}

        # metrics
        self._metrics = _metrics.Metrics.get_namespace(namespace)

    # Key helpers -------------------------------------------------
    def _full_key(self, key: str) -> str:
        return f"{self.namespace}::{key}"

    # Basic ops --------------------------------------------------
    def get(self, key: str) -> Optional[Any]:
        full = self._full_key(key)
        with self._lock:
            entry = self._data.get(full)
            if not entry:
                self._metrics.increment("miss")
                return None
            if entry.is_expired():
                # remove expired
                self._data.pop(full, None)
                self._metrics.increment("expired")
                return None
            # promote
            self._data.move_to_end(full)
            self._metrics.increment("hit")
            return entry.value

    def set(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        full = self._full_key(key)
        ttl = self.default_ttl if ttl is None else ttl
        with self._lock:
            if full in self._data:
                # overwrite and promote
                self._data.pop(full)
            self._data[full] = CacheEntry(value, ttl)
            self._data.move_to_end(full)
            self._metrics.increment("set")
            self._maybe_evict()

    def _maybe_evict(self) -> None:
        while len(self._data) > self.capacity:
            k, _ = self._data.popitem(last=False)
            self._metrics.increment("eviction")
            # eviction reason logged via metrics; caller may inspect key

    def invalidate_namespace(self) -> None:
        with self._lock:
            removed = len(self._data)
            self._data.clear()
            self._metrics.increment("invalidate")
            return removed

    def inspect_keys(self, prefix: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
        with self._lock:
            out = {}
            for k, v in self._data.items():
                if prefix and not k.startswith(self._full_key(prefix)):
                    continue
                out[k] = {"created_at": v.created_at, "expiry": v.expiry}
            return out

    # Request coalescing: compute once, others wait ----------------
    def get_or_compute(self, key: str, compute_fn: Callable[[], Any], ttl: Optional[float] = None, timeout: Optional[float] = None) -> Any:
        """Return cached value or compute it atomically. compute_fn runs under the first caller only.

        Other callers block on the same Future and receive the result (or exception).
        """
        # fast path
        val = self.get(key)
        if val is not None:
            return val

        full = self._full_key(key)
        with self._lock:
            future = self._in_flight.get(full)
            if future is None:
                future = concurrent.futures.Future()
                self._in_flight[full] = future
                is_owner = True
            else:
                is_owner = False

        if not is_owner:
            # wait for owner to compute
            try:
                result = future.result(timeout=timeout)
                self._metrics.increment("coalesced")
                return result
            except concurrent.futures.TimeoutError as e:
                self._metrics.increment("coalesce_timeout")
                raise CacheError("Timed out waiting for in-flight computation") from e

        # owner computes
        try:
            result = compute_fn()
            # store
            self.set(key, result, ttl=ttl)
            future.set_result(result)
            return result
        except Exception as exc:
            future.set_exception(exc)
            raise
        finally:
            with self._lock:
                self._in_flight.pop(full, None)

    # Admin helpers ------------------------------------------------
    def prewarm(self, items: Dict[str, Tuple[Any, Optional[float]]]) -> None:
        with self._lock:
            for k, (v, t) in items.items():
                self.set(k, v, ttl=t)


# convenience factory
def make_cache(namespace: str, capacity: int = 1024, default_ttl: Optional[float] = 300) -> NamespacedLRUCache:
    return NamespacedLRUCache(capacity=capacity, default_ttl=default_ttl, namespace=namespace)
