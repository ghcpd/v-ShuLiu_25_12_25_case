"""Lightweight in-process metrics for tests and development.

Provides namespace-scoped counters and simple snapshots used by tests.
"""
from __future__ import annotations

import threading
from collections import defaultdict
from typing import Dict


class Metrics:
    _namespaces: Dict[str, "Metrics"] = {}
    _global_lock = threading.Lock()

    def __init__(self, namespace: str):
        self.namespace = namespace
        self._counters = defaultdict(int)
        self._lock = threading.Lock()

    @classmethod
    def get_namespace(cls, namespace: str) -> "Metrics":
        with cls._global_lock:
            if namespace not in cls._namespaces:
                cls._namespaces[namespace] = Metrics(namespace)
            return cls._namespaces[namespace]

    def increment(self, key: str, amount: int = 1) -> None:
        with self._lock:
            self._counters[key] += amount

    def get_snapshot(self) -> Dict[str, int]:
        with self._lock:
            return dict(self._counters)

    def reset(self) -> None:
        with self._lock:
            self._counters.clear()
