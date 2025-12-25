"""View interface: each view exposes parse/plot/download and uses the pipeline primitives."""
from __future__ import annotations

from typing import Any, Dict


class ViewBase:
    endpoint_id: str

    def parse(self, request: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError

    def plot(self, request: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError

    def download(self, request: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError
