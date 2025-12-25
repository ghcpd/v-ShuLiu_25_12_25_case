"""Parse endpoint view placeholder."""
from typing import Dict, Any
from ..cache.lru import LRUCacheManager


def handle_parse(request: Dict[str, Any], endpoint_id: str, cache: LRUCacheManager) -> Dict[str, Any]:
    # parse-only endpoint; for now reuse plot semantics
    request = dict(request)
    request["requestType"] = "parse"
    from .plot import handle_plot
    return handle_plot(request, endpoint_id, cache)
