from .cache.lru import cache_manager

def get_cache_metrics():
    return cache_manager.get_metrics()

def log_metrics():
    metrics = get_cache_metrics()
    print("Cache Metrics:", metrics)