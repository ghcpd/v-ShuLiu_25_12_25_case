"""Thread-safe namespaced LRU cache with TTL and request coalescing."""
from __future__ import annotations

import json
import threading
import time
from collections import OrderedDict
from concurrent.futures import Future
from typing import Any, Callable, Dict, Optional, Tuple

from .. import metrics as _metrics


class CacheEntry:
    def __init__(self, value: Any, ts: float, ttl: Optional[float]):
        self.value = value
        self.ts = ts
        self.ttl = ttl

    def is_expired(self, now: Optional[float] = None) -> bool:
        now = now if now is not None else time.time()
        return self.ttl is not None and (self.ts + self.ttl) < now


class LRUCacheManager:
    def __init__(self, capacity: int = 1024, default_ttl: Optional[float] = None):
        self.capacity = int(capacity)
        self.default_ttl = default_ttl
        self._lock = threading.RLock()
        # namespace -> OrderedDict[key -> CacheEntry]
        self._namespaces: Dict[str, OrderedDict] = {}
        # in-flight computations: namespace -> key -> Future
        self._inflight: Dict[str, Dict[str, Future]] = {}

    def _ensure_namespace(self, ns: str) -> None:
        with self._lock:
            if ns not in self._namespaces:
                self._namespaces[ns] = OrderedDict()
                self._inflight[ns] = {}

    def _make_key(self, *, module: str, endpoint_id: str, request_type: str, config_version: str,
                  time_start: str, time_end: str, time_step: str, train_no: str, carriage: str,
                  parse_mode: str, extras: Optional[Dict] = None) -> Tuple[str, str]:
        # namespace is module:endpoint
        namespace = f"{module}:{endpoint_id}"
        key_payload = {
            "request_type": request_type,
            "config_version": config_version,
            "time_start": time_start,
            "time_end": time_end,
            "time_step": time_step,
            "train_no": train_no,
            "carriage": carriage,
            "parse_mode": parse_mode,
        }
        if extras:
            key_payload.update(extras)
        # canonical JSON for stable hashing
        key = json.dumps(key_payload, sort_keys=True, separators=(",", ":"))
        return namespace, key

    def _evict_if_needed(self, ns: str) -> None:
        store = self._namespaces[ns]
        while len(store) > self.capacity:
            k, _ = store.popitem(last=False)
            _metrics.increment("cache.evicted")

    def get(self, ns: str, key: str) -> Optional[Any]:
        with self._lock:
            store = self._namespaces.get(ns)
            if not store:
                _metrics.increment("cache.miss")
                return None
            entry: CacheEntry = store.get(key)
            if not entry:
                _metrics.increment("cache.miss")
                return None
            if entry.is_expired():
                # remove stale
                del store[key]
                _metrics.increment("cache.expired")
                return None
            # move to end = recently used
            store.move_to_end(key, last=True)
            _metrics.increment("cache.hit")
            return entry.value

    def set(self, ns: str, key: str, value: Any, ttl: Optional[float] = None) -> None:
        with self._lock:
            self._ensure_namespace(ns)
            store = self._namespaces[ns]
            store[key] = CacheEntry(value=value, ts=time.time(), ttl=ttl if ttl is not None else self.default_ttl)
            store.move_to_end(key, last=True)
            self._evict_if_needed(ns)
            _metrics.increment("cache.set")

    def clear_namespace(self, ns: str) -> None:
        with self._lock:
            if ns in self._namespaces:
                self._namespaces[ns].clear()
                _metrics.increment("cache.cleared")

    def inspect_namespace(self, ns: str) -> Dict[str, Any]:
        with self._lock:
            store = self._namespaces.get(ns)
            if not store:
                return {"size": 0, "keys": []}
            keys = list(store.keys())
            return {"size": len(store), "keys": keys}

    def get_or_compute(self, *, module: str, endpoint_id: str, request_type: str,
                       config_version: str, time_start: str, time_end: str, time_step: str,
                       train_no: str, carriage: str, parse_mode: str, compute_fn: Callable[[], Any],
                       ttl: Optional[float] = None, extras: Optional[Dict] = None) -> Any:
        ns, key = self._make_key(module=module, endpoint_id=endpoint_id, request_type=request_type,
                                  config_version=config_version, time_start=time_start,
                                  time_end=time_end, time_step=time_step, train_no=train_no,
                                  carriage=carriage, parse_mode=parse_mode, extras=extras)
        self._ensure_namespace(ns)
        # fast path
        val = self.get(ns, key)
        if val is not None:
            return val
        # coalesce in-flight computations
        with self._lock:
            inflight_ns = self._inflight[ns]
            fut = inflight_ns.get(key)
            if fut is not None:
                # another thread is computing this key
                _metrics.increment("cache.coalesced")
                i_am_leader = False
            else:
                fut = Future()
                inflight_ns[key] = fut
                i_am_leader = True
        if i_am_leader:
            try:
                result = compute_fn()
                self.set(ns, key, result, ttl=ttl)
                try:
                    fut.set_result(result)
                except Exception:
                    # future may already be finished; ignore
                    pass
            except Exception as exc:
                try:
                    fut.set_exception(exc)
                except Exception:
                    pass
                raise
            finally:
                # cleanup in-flight
                with self._lock:
                    inflight_ns.pop(key, None)
        else:
            # wait for result from the leader
            result = fut.result()
        return result

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            return {ns: {"size": len(store)} for ns, store in self._namespaces.items()}
