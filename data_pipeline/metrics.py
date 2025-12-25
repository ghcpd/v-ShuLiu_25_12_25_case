"""Simple in-memory metrics counters for tests and local debug."""
from collections import Counter
from threading import Lock

metrics = Counter()
_metrics_lock = Lock()


def increment(name: str, amount: int = 1) -> None:
    with _metrics_lock:
        metrics[name] += amount


def get(name: str) -> int:
    with _metrics_lock:
        return metrics.get(name, 0)


def reset() -> None:
    with _metrics_lock:
        metrics.clear()
