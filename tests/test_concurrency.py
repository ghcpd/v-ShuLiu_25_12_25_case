import threading
from concurrent.futures import ThreadPoolExecutor

from data_pipeline.cache.lru import NamespacedLRU


def test_concurrent_get_or_compute_coalescing():
    cache = NamespacedLRU(capacity=10, default_ttl=60)
    key = "shared-key"
    namespace = "ns"
    counter = {"calls": 0}

    def factory():
        counter["calls"] += 1
        # simulate work
        import time
        time.sleep(0.1)
        return "computed"

    def worker():
        return cache.get_or_compute(namespace, key, factory)

    with ThreadPoolExecutor(max_workers=8) as ex:
        results = list(ex.map(lambda _: worker(), range(8)))

    assert all(r == "computed" for r in results)
    # factory should have been called exactly once because of coalescing
    assert counter["calls"] == 1

