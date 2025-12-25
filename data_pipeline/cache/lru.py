import time
import threading
from typing import Any, Dict, Tuple, Optional, Callable
from cachetools import TTLCache
from collections import defaultdict
from concurrent.futures import Future

class LRUCacheManager:
    def __init__(self, default_capacity: int = 1000, default_ttl: int = 3600):
        self.namespaces: Dict[str, TTLCache] = {}
        self.locks: Dict[str, threading.RLock] = {}
        self.futures: Dict[str, Dict[Any, Future]] = defaultdict(dict)
        self.metrics = {
            'hits': defaultdict(int),
            'misses': defaultdict(int),
            'evictions': defaultdict(int),
            'sets': defaultdict(int),
        }
        self.default_capacity = default_capacity
        self.default_ttl = default_ttl

    def get_or_compute(self, namespace: str, key: Tuple, compute_func: Callable[[], Any]) -> Any:
        with self.locks.setdefault(namespace, threading.RLock()):
            cache = self.namespaces.setdefault(namespace, TTLCache(self.default_capacity, self.default_ttl))
            if key in cache:
                self.metrics['hits'][namespace] += 1
                return cache[key]
            else:
                self.metrics['misses'][namespace] += 1
                # Check if already computing
                if key in self.futures[namespace]:
                    return self.futures[namespace][key].result()
                # Compute
                future = self.futures[namespace][key] = Future()
                try:
                    value = compute_func()
                    cache[key] = value
                    self.metrics['sets'][namespace] += 1
                    future.set_result(value)
                    return value
                except Exception as e:
                    future.set_exception(e)
                    raise
                finally:
                    del self.futures[namespace][key]

    def set(self, namespace: str, key: Tuple, value: Any, ttl: Optional[int] = None):
        with self.locks.setdefault(namespace, threading.RLock()):
            cache = self.namespaces.setdefault(namespace, TTLCache(self.default_capacity, self.default_ttl))
            cache[key] = value
            if ttl:
                # Note: TTLCache sets TTL on creation, this is simplified
                pass
            self.metrics['sets'][namespace] += 1

    def get(self, namespace: str, key: Tuple) -> Optional[Any]:
        with self.locks.setdefault(namespace, threading.RLock()):
            cache = self.namespaces.get(namespace)
            if cache and key in cache:
                self.metrics['hits'][namespace] += 1
                return cache[key]
            else:
                self.metrics['misses'][namespace] += 1
                return None

    def clear_namespace(self, namespace: str):
        with self.locks.setdefault(namespace, threading.RLock()):
            if namespace in self.namespaces:
                self.namespaces[namespace].clear()

    def get_metrics(self, namespace: str = None) -> Dict:
        if namespace:
            return dict(self.metrics)
        else:
            return {k: dict(v) for k, v in self.metrics.items()}

    def prewarm(self, namespace: str, keys_values: Dict[Tuple, Any]):
        with self.locks.setdefault(namespace, threading.RLock()):
            cache = self.namespaces.setdefault(namespace, TTLCache(self.default_capacity, self.default_ttl))
            for key, value in keys_values.items():
                cache[key] = value
                self.metrics['sets'][namespace] += 1

# Global instance
cache_manager = LRUCacheManager()