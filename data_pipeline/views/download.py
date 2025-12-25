"""Download view placeholder."""
from typing import Dict, Any
from ..cache.lru import LRUCacheManager


def handle_download(request: Dict[str, Any], endpoint_id: str, cache: LRUCacheManager) -> Dict[str, Any]:
    # For downloads, treat similar to plot but may include different downstream handling
    request = dict(request)
    request["requestType"] = "download"
    return handle_plot_or_passthrough(request, endpoint_id, cache)


def handle_plot_or_passthrough(request: Dict[str, Any], endpoint_id: str, cache: LRUCacheManager) -> Dict[str, Any]:
    from .plot import handle_plot
    return handle_plot(request, endpoint_id, cache)
