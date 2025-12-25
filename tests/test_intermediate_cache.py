from compat import parse, plot

import json


def _load_config():
    with open("data/sample_config_v1.json", "r", encoding="utf-8") as f:
        return json.load(f)


def test_primary_and_secondary_caching(tmp_path):
    cfg = _load_config()
    # construct two requests identical except request_type
    req = {
        "endpoint_id": "e1",
        "type": "parse",
        "config": cfg,
        "time_start": "2025-01-01T00:00:00Z",
        "time_end": "2025-01-01T00:01:00Z",
        "step": 1,
        "train_no": "1",
        "carriage": "A",
        "second_parse": cfg.get("second_parse", {}),
        "cache_ttl": 60,
    }
    with open("data/mvb_sample.bin", "rb") as f:
        raw = f.read()
    frames = parse("MVB", raw, req)
    assert isinstance(frames, list)
    # secondary
    metrics = plot("MVB", frames, req)
    assert isinstance(metrics, dict)
    # calling plot again should reuse cached secondary result (coalescing/hit)
    metrics2 = plot("MVB", frames, req)
    assert metrics == metrics2

