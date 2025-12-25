"""Very small backward-compatible wrappers over the new pipeline for tests."""
from typing import Dict
from ..data_pipeline.cache.lru import LRUCacheManager
from ..data_pipeline.views import handle_plot, handle_download, handle_parse

# single global cache used by legacy wrapper for simplicity
_global_cache = LRUCacheManager(capacity=512, default_ttl=60.0)


def plot(request: Dict, endpoint_id: str = "legacy.plot"):
    return handle_plot(request, endpoint_id, _global_cache)


def download(request: Dict, endpoint_id: str = "legacy.download"):
    return handle_download(request, endpoint_id, _global_cache)


def parse(request: Dict, endpoint_id: str = "legacy.parse"):
    return handle_parse(request, endpoint_id, _global_cache)
