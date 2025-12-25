"""data_pipeline package - small, test-oriented skeleton for LRU-centric parsing system."""
__all__ = [
    "cache",
    "parsers",
    "views",
    "sources",
    "config",
    "validators",
    "routing",
    "metrics",
    "errors",
    "logging_utils",
]

from .cache import lru as lru_cache  # convenience import
from .metrics import Metrics

__version__ = "0.1.0"
