"""Tests for LRU cache behavior: key correctness, namespace isolation, TTL, and coalescing."""
import threading
import time
from data_pipeline.cache.lru import LRUCacheManager
from data_pipeline.metrics import reset, metrics


def test_key_semantics_and_namespace_isolation():
    cache = LRUCacheManager(capacity=10, default_ttl=10)

    req1 = dict(module="MVB", endpoint_id="viewA", request_type="plot", config_version="v1",
                time_start="2025-12-25T08:00:00Z", time_end="2025-12-25T09:00:00Z", time_step="1s",
                train_no="G1234", carriage="01", parse_mode="standard")

    req2 = dict(req1)
    req2["time_step"] = "2s"  # should be different key

    called = {"count": 0}

    def compute1():
        called["count"] += 1
        return {"ok": 1}

    r1 = cache.get_or_compute(module=req1["module"], endpoint_id=req1["endpoint_id"], request_type=req1["request_type"],
                              config_version=req1["config_version"], time_start=req1["time_start"], time_end=req1["time_end"],
                              time_step=req1["time_step"], train_no=req1["train_no"], carriage=req1["carriage"],
                              parse_mode=req1["parse_mode"], compute_fn=compute1)

    r2 = cache.get_or_compute(module=req2["module"], endpoint_id=req2["endpoint_id"], request_type=req2["request_type"],
                              config_version=req2["config_version"], time_start=req2["time_start"], time_end=req2["time_end"],
                              time_step=req2["time_step"], train_no=req2["train_no"], carriage=req2["carriage"],
                              parse_mode=req2["parse_mode"], compute_fn=lambda: {"ok": 2})

    assert r1 != r2
    assert called["count"] == 1


def test_ttl_and_version_isolation():
    cache = LRUCacheManager(capacity=10, default_ttl=0.5)

    def compute_v1():
        return {"v": 1}

    v = cache.get_or_compute(module="MVB", endpoint_id="vtest", request_type="plot",
                             config_version="v1", time_start="t1", time_end="t2", time_step="1s",
                             train_no="G1", carriage="01", parse_mode="standard", compute_fn=compute_v1)
    assert v["v"] == 1

    # wait beyond ttl
    time.sleep(0.7)

    called = {"count": 0}
    def compute_v1b():
        called["count"] += 1
        return {"v": 1}

    # should recompute
    v2 = cache.get_or_compute(module="MVB", endpoint_id="vtest", request_type="plot",
                              config_version="v1", time_start="t1", time_end="t2", time_step="1s",
                              train_no="G1", carriage="01", parse_mode="standard", compute_fn=compute_v1b)
    assert called["count"] == 1

    # version bump -> different key
    v3 = cache.get_or_compute(module="MVB", endpoint_id="vtest", request_type="plot",
                              config_version="v2", time_start="t1", time_end="t2", time_step="1s",
                              train_no="G1", carriage="01", parse_mode="standard", compute_fn=lambda: {"v": 2})
    assert v3["v"] == 2


def test_concurrency_coalescing():
    cache = LRUCacheManager(capacity=10, default_ttl=10)
    calls = {"count": 0}

    def compute_slow():
        calls["count"] += 1
        time.sleep(0.2)
        return {"done": True}

    def worker(results, idx):
        res = cache.get_or_compute(module="MVB", endpoint_id="coalesce", request_type="plot",
                                   config_version="v1", time_start="tstart", time_end="tend", time_step="1s",
                                   train_no="G", carriage=str(idx%2), parse_mode="standard", compute_fn=compute_slow)
        results[idx] = res

    threads = []
    results = {}
    for i in range(10):
        t = threading.Thread(target=worker, args=(results, i))
        threads.append(t)
        t.start()
    for t in threads:
        t.join()

    # ensure compute called once or few times depending on carriage (two different keys by carriage)
    assert calls["count"] <= 2
