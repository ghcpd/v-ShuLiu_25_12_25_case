"""MVB View: demonstrates namespaced cache keys, primary/secondary caching, and request coalescing."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict
import time

from ..cache.lru import make_cache
from ..parsers.mvb import MVBParser
from ..sources.minio import fetch_time_window
from ..config.loader import load_config
from ..validators.schema import RequestSchema


def _make_key(request: RequestSchema, endpoint_id: str, suffix: str) -> str:
    # structured, deterministic key (do NOT include view impl)
    parts = [
        f"module={request.module}",
        f"endpoint={endpoint_id}",
        f"type={request.requestType}",
        f"cfg={request.configVersion}",
        f"ts={request.timeStart.isoformat()}",
        f"te={request.timeEnd.isoformat()}",
        f"step={request.timeStep}",
        f"train={request.trainNo}",
        f"carriage={request.carriage}",
        f"mode={request.parse_mode or 'standard'}",
        f"sfx={suffix}",
    ]
    return "|".join(parts)


class MVBView:
    endpoint_id = "mvb.plot"

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.parser = MVBParser()
        # two caches: primary (parsed frames) and secondary (aggregations/plots)
        self.primary_cache = make_cache("mvb.primary", capacity=256, default_ttl=300)
        self.secondary_cache = make_cache("mvb.secondary", capacity=512, default_ttl=120)

    def _load_config(self, version: str):
        return load_config(version, self.data_dir)

    def parse(self, request: RequestSchema) -> Dict[str, Any]:
        key = _make_key(request, self.endpoint_id, "parsed")

        def compute():
            cfg = self._load_config(request.configVersion)
            # convert ISO times to simple integer seconds for test adapter
            ts = int(request.timeStart.timestamp())
            te = int(request.timeEnd.timestamp())
            raw = fetch_time_window(self.data_dir / "mvb_sample.bin", ts, te, frame_size=4, parallel=True, frames_per_second=1, slice_seconds=30, parallelism=4, delay=0.001)
            parsed = self.parser.parse_bytes(raw, cfg)
            # store a small metadata blob plus parsed count
            return {"meta": parsed.meta, "frames": parsed.frames}

        return self.primary_cache.get_or_compute(key, compute)

    def plot(self, request: RequestSchema) -> Dict[str, Any]:
        # secondary caching layered on primary
        s_key = _make_key(request, self.endpoint_id, "plot")

        def compute_plot():
            parsed = self.parse(request)
            # simple downsample: take every Nth based on timeStep
            step = int(request.timeStep.rstrip("s")) if request.timeStep.endswith("s") else 1
            down = [f for i, f in enumerate(parsed["frames"]) if (i % step) == 0]
            metrics = {"count": len(parsed["frames"]), "downsampled": len(down)}
            return {"metrics": metrics, "points": down}

        return self.secondary_cache.get_or_compute(s_key, compute_plot)

    def download(self, request: RequestSchema) -> Dict[str, Any]:
        # downloads should not accidentally hit plot cache — different key namespace
        key = _make_key(request, self.endpoint_id, "download")

        def compute_dl():
            parsed = self.parse(request)
            # convert to CSV-like bytes
            rows = ["idx,speed,temp"]
            for r in parsed["frames"]:
                rows.append(f"{r['idx']},{r['speed']},{r['temp']}")
            return {"bytes": "\n".join(rows).encode("utf-8")}

        return self.secondary_cache.get_or_compute(key, compute_dl)
