import time

from data_pipeline.cache.lru import NamespacedLRU


def test_ttl_and_version_isolation():
    cache = NamespacedLRU(capacity=10, default_ttl=1)
    key_v1 = cache.make_key(module="MVB", endpoint_id="e1", request_type="parse", config_version="v1",
                             time_start="t0", time_end="t1", time_step=1, train_no="1", carriage="A", parse_mode="standard")
    key_v2 = cache.make_key(module="MVB", endpoint_id="e1", request_type="parse", config_version="v2",
                             time_start="t0", time_end="t1", time_step=1, train_no="1", carriage="A", parse_mode="standard")
    cache.set("ns", key_v1, "old", ttl=1)
    cache.set("ns", key_v2, "new", ttl=1)
    assert cache.get("ns", key_v1) == "old"
    time.sleep(1.1)
    # both expired
    assert cache.get("ns", key_v1) is None
    assert cache.get("ns", key_v2) is None

