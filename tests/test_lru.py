import threading
import time

from data_pipeline.cache.lru import NamespacedLRU


def test_namespaced_key_uniqueness():
    cache = NamespacedLRU(capacity=10, default_ttl=60)
    k1 = cache.make_key(module="MVB", endpoint_id="e1", request_type="parse", config_version="v1",
                        time_start="t0", time_end="t1", time_step=1, train_no="1", carriage="A", parse_mode="standard")
    k2 = cache.make_key(module="MVB", endpoint_id="e1", request_type="parse", config_version="v1",
                        time_start="t0", time_end="t1", time_step=2, train_no="1", carriage="A", parse_mode="standard")
    assert k1 != k2
    cache.set("ns", k1, "val1")
    assert cache.get("ns", k1) == "val1"
    assert cache.get("ns", k2) is None


def test_eviction_order_and_capacity():
    cache = NamespacedLRU(capacity=2, default_ttl=60)
    cache.set("ns", "a", 1)
    cache.set("ns", "b", 2)
    cache.set("ns", "c", 3)
    ns_info = cache.inspect_namespace("ns")
    assert ns_info["size"] == 2

