"""In-memory metrics registry (small, testable)."""
from __future__ import annotations

from collections import Counter
from typing import Dict, Any


class MetricsRegistry:
    def __init__(self):
        self._c = Counter()

    def incr(self, key: str, n: int = 1):
        self._c[key] += n

    def get(self, key: str) -> int:
        return self._c.get(key, 0)

    def snapshot(self) -> Dict[str, int]:
        return dict(self._c)


metrics = MetricsRegistry()
