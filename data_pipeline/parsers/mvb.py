"""Minimal placeholder MVB parser.
- Converts bytes -> list of frames (dicts) using config.signal_map
"""
from __future__ import annotations

from typing import Dict, Any, List
import struct


def parse_mvb_bytes(raw: bytes, config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Very small deterministic parser for sample data.

    Interprets raw bytes as consecutive little-endian unsigned shorts (2 bytes) and maps to signals
    according to config.signal_map. Returns list of frames where each frame contains mapped signals.
    """
    signal_map = config.get("signal_map", {})
    # interpret as little-endian unsigned shorts
    vals = list(struct.unpack(f"<{len(raw)//2}H", raw[: (len(raw)//2)*2 ]))
    frames = []
    # assume each frame contains N signals where N = sum(lengths)
    per_frame_len = sum(v.get("length", 0) for v in signal_map.values())
    if per_frame_len == 0:
        return frames
    for i in range(0, len(vals), per_frame_len):
        chunk = vals[i:i+per_frame_len]
        if len(chunk) < per_frame_len:
            break
        frame = {}
        idx = 0
        for name, meta in signal_map.items():
            length = meta.get("length", 1)
            scale = meta.get("scale", 1.0)
            # simplify: take first value if length>1
            raw_val = chunk[idx]
            frame[name] = raw_val * scale
            idx += length
        frames.append(frame)
    return frames
