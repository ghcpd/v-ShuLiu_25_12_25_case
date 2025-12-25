"""Minimal PHM parser placeholder."""
from datetime import datetime, timedelta
from typing import Dict, Any


def parse_phm(raw_data: bytes, config: Dict[str, Any], time_start: str, time_end: str, time_step: str) -> Dict[str, Any]:
    # For tests, produce a different deterministic output so caches don't collide
    start = datetime.fromisoformat(time_start.replace("Z", "+00:00"))
    end = datetime.fromisoformat(time_end.replace("Z", "+00:00"))
    step_seconds = int(time_step.rstrip("s"))
    samples = []
    cur = start
    i = 0
    while cur < end:
        samples.append({"t": cur.isoformat(), "v": (i % 50) * 0.2})
        cur += timedelta(seconds=step_seconds)
        i += 1
    metrics = {"v_sum": sum(s["v"] for s in samples)}
    return {"samples": samples, "metrics": metrics, "config_version": config.get("version")}
