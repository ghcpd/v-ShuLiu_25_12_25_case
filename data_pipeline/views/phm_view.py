"""PHM View placeholder mirroring MVBView behaviour."""
from __future__ import annotations

from typing import Any, Dict, List
from ..cache import NamespacedLRU
from ..parsers import parse_phm_bytes

CACHE_NS = "phm"


class PHMView:
    def __init__(self, cache: NamespacedLRU):
        self.cache = cache

    def _primary_key(self, request: Dict[str, Any]) -> str:
        return self.cache.make_key(module="PHM", endpoint_id=request["endpoint_id"], request_type=request["type"],
                                   config_version=request["config"]["version"], time_start=request["time_start"],
                                   time_end=request["time_end"], time_step=request["step"], train_no=request.get("train_no",""),
                                   carriage=request.get("carriage",""), parse_mode=request["config"].get("parse_mode","standard"))

    def parse(self, raw: bytes, request: Dict[str, Any]) -> List[Dict[str, Any]]:
        key = self._primary_key(request)

        def factory():
            frames = parse_phm_bytes(raw, request["config"])  # primary parse
            return frames

        return self.cache.get_or_compute(CACHE_NS, key, factory, ttl=request.get("cache_ttl"))

    def plot_metrics(self, frames: List[Dict[str, Any]], request: Dict[str, Any]) -> Dict[str, Any]:
        primary_key = self._primary_key(request)
        secondary_key = primary_key + "|secondary:plot_metrics:" + ",".join(request.get("second_parse", {}).get("plot_metrics", []))

        def factory():
            metrics = {}
            metrics_list = request.get("second_parse", {}).get("plot_metrics", [])
            for m in metrics_list:
                if m == "health_avg":
                    vals = [f.get("health", 0) for f in frames]
                    metrics["health_avg"] = sum(vals) / max(1, len(vals))
            return metrics

        return self.cache.get_or_compute(CACHE_NS, secondary_key, factory, ttl=request.get("cache_ttl"))
