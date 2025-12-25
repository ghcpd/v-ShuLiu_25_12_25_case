"""Minimal MVB parser placeholder."""
from datetime import datetime, timedelta
from typing import Dict, Any, List


def parse_mvb(raw_data: bytes, config: Dict[str, Any], time_start: str, time_end: str, time_step: str) -> Dict[str, Any]:
    # For testing, synthesize deterministic time-series based on time window and step
    start = datetime.fromisoformat(time_start.replace("Z", "+00:00"))
    end = datetime.fromisoformat(time_end.replace("Z", "+00:00"))
    step_seconds = int(time_step.rstrip("s"))
    samples = []
    cur = start
    i = 0
    while cur < end:
        # deterministic values using i and config version
        samples.append({"t": cur.isoformat(), "speed": (i % 100) * 0.1, "temp": ((i * 3) % 100) * 0.1})
        cur += timedelta(seconds=step_seconds)
        i += 1
    # pretend we did primary parse + secondary metrics
    metrics = {"speed_avg": sum(s["speed"] for s in samples) / max(1, len(samples))}
    return {"samples": samples, "metrics": metrics, "config_version": config.get("version")}
