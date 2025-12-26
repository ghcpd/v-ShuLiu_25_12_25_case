"""
Compatibility layer preserving legacy API semantics.
Bridges old mini-program API to new modular pipeline.
"""

from typing import Dict, Any, Optional
from data_pipeline import (
    Router,
    NamespacedLRUCache,
    setup_logging,
    set_request_context,
)
from data_pipeline.logging_utils import get_context_logger

# Setup logging
setup_logging()
logger = get_context_logger(__name__)

# Global state
_global_cache: Optional[NamespacedLRUCache] = None
_global_router: Optional[Router] = None


def initialize(config_dir: str = "data", cache_size: int = 1000, default_ttl: int = 3600) -> None:
    """Initialize the system with cache and router."""
    global _global_cache, _global_router
    
    _global_cache = NamespacedLRUCache(max_size=cache_size, default_ttl_seconds=default_ttl)
    _global_router = Router(_global_cache, config_dir)
    
    logger.info(f"Initialized system: cache_size={cache_size}, ttl={default_ttl}s")


def parse(
    module: str,
    config_version: str,
    time_start: str,
    time_end: str,
    time_step: str,
    train_no: str,
    carriage: str,
    parse_mode: str = "standard",
) -> Dict[str, Any]:
    """
    Legacy parse() entry point.
    
    Returns response dict with status, data, or error.
    """
    if _global_router is None:
        initialize()
    
    request = {
        "module": module,
        "requestType": "parse",
        "configVersion": config_version,
        "timeStart": time_start,
        "timeEnd": time_end,
        "timeStep": time_step,
        "trainNo": train_no,
        "carriage": carriage,
        "parseMode": parse_mode,
    }
    
    return _global_router.dispatch(request)


def plot(
    module: str,
    config_version: str,
    time_start: str,
    time_end: str,
    time_step: str,
    train_no: str,
    carriage: str,
) -> Dict[str, Any]:
    """
    Legacy plot() entry point.
    
    Returns response dict with plot data and cache status.
    """
    if _global_router is None:
        initialize()
    
    request = {
        "module": module,
        "requestType": "plot",
        "configVersion": config_version,
        "timeStart": time_start,
        "timeEnd": time_end,
        "timeStep": time_step,
        "trainNo": train_no,
        "carriage": carriage,
    }
    
    return _global_router.dispatch(request)


def download(
    module: str,
    config_version: str,
    time_start: str,
    time_end: str,
    time_step: str,
    train_no: str,
    carriage: str,
) -> Dict[str, Any]:
    """
    Legacy download() entry point.
    
    Returns response dict with export data.
    """
    if _global_router is None:
        initialize()
    
    request = {
        "module": module,
        "requestType": "download",
        "configVersion": config_version,
        "timeStart": time_start,
        "timeEnd": time_end,
        "timeStep": time_step,
        "trainNo": train_no,
        "carriage": carriage,
    }
    
    return _global_router.dispatch(request)


def get_cache() -> Optional[NamespacedLRUCache]:
    """Get global cache instance."""
    return _global_cache


def get_metrics() -> Dict[str, Any]:
    """Get current metrics."""
    if _global_cache is None:
        return {}
    
    from data_pipeline.metrics import MetricsCollector
    return MetricsCollector.get_instance().to_dict()


def clear_cache(namespace: Optional[str] = None) -> int:
    """Clear cache (all or specific namespace)."""
    if _global_cache is None:
        return 0
    
    if namespace:
        return _global_cache.clear_namespace(namespace)
    else:
        return _global_cache.clear_all()
