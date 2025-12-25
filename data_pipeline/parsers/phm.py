"""Minimal placeholder PHM parser.
"""
from __future__ import annotations

from typing import Dict, Any, List


def parse_phm_bytes(raw: bytes, config: Dict[str, Any]) -> List[Dict[str, Any]]:
    # PHM sample parser returns a sequence of synthetic health metrics parsed from bytes
    frames = []
    # simple: chunk bytes into groups of 4 and interpret sum / 100.0 as metric
    for i in range(0, len(raw), 4):
        chunk = raw[i:i+4]
        if len(chunk) < 4:
            break
        val = int.from_bytes(chunk, "little")
        frames.append({"health": (val % 10000) / 100.0})
    return frames
