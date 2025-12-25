"""Compatibility shim exposing legacy parse/plot/download signatures while delegating to new Views."""
from pathlib import Path
from typing import Dict, Any

from data_pipeline.views.mvb_view import MVBView
from data_pipeline.validators.schema import RequestSchema


_data_dir = Path(__file__).resolve().parents[1] / "data"
_mvb = MVBView(_data_dir)


def parse(request: Dict[str, Any]) -> Dict[str, Any]:
    req = RequestSchema.parse_obj(request)
    return _mvb.parse(req)


def plot(request: Dict[str, Any]) -> Dict[str, Any]:
    req = RequestSchema.parse_obj(request)
    return _mvb.plot(req)


def download(request: Dict[str, Any]) -> Dict[str, Any]:
    req = RequestSchema.parse_obj(request)
    return _mvb.download(req)
