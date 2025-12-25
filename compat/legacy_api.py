"""Backward-compatible API that delegates to new views and cache.
This module exposes parse/plot/download functions matching the old signatures.
"""
from __future__ import annotations

from typing import Dict, Any, List
from data_pipeline.cache.lru import NamespacedLRU
from data_pipeline.views.mvb_view import MVBView
from data_pipeline.views.phm_view import PHMView

# single shared cache instance for demo
_cache = NamespacedLRU(capacity=1024, default_ttl=300)
_mvb = MVBView(_cache)
_phm = PHMView(_cache)


def parse(module: str, raw: bytes, request: Dict[str, Any]) -> List[Dict[str, Any]]:
    if module.upper() == "MVB":
        return _mvb.parse(raw, request)
    if module.upper() == "PHM":
        return _phm.parse(raw, request)
    raise ValueError("unknown module")


def plot(module: str, frames: List[Dict[str, Any]], request: Dict[str, Any]) -> Dict[str, Any]:
    if module.upper() == "MVB":
        return _mvb.plot_metrics(frames, request)
    if module.upper() == "PHM":
        return _phm.plot_metrics(frames, request)
    raise ValueError("unknown module")


def download(module: str, frames: List[Dict[str, Any]], request: Dict[str, Any]) -> bytes:
    if module.upper() == "MVB":
        return _mvb.download(frames, request)
    if module.upper() == "PHM":
        return b""
    raise ValueError("unknown module")
