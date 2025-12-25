import pytest
from data_pipeline.cache.lru import cache_manager

def test_cache_get_set():
    key = ('test', 'key')
    namespace = 'test_ns'
    value = 'test_value'
    cache_manager.set(namespace, key, value)
    assert cache_manager.get(namespace, key) == value

def test_cache_miss():
    key = ('miss', 'key')
    namespace = 'test_ns'
    assert cache_manager.get(namespace, key) is None

def test_get_or_compute():
    key = ('compute', 'key')
    namespace = 'test_ns'
    def compute():
        return 'computed_value'
    result = cache_manager.get_or_compute(namespace, key, compute)
    assert result == 'computed_value'
    # Second call should hit cache
    result2 = cache_manager.get_or_compute(namespace, key, lambda: 'should_not_call')
    assert result2 == 'computed_value'

def test_metrics():
    metrics = cache_manager.get_metrics()
    assert 'hits' in metrics
    assert 'misses' in metrics