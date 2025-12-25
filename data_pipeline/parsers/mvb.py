"""MVB parser: tiny, deterministic mapping used for tests."""
from __future__ import annotations

import struct
from typing import Any, Dict, List

from .base import Parser, ParseResult


class MVBParser(Parser):
    FRAME_SIZE = 4  # 2 bytes speed, 2 bytes temp (as in sample_config_v1.json)

    def parse_bytes(self, data: bytes, config) -> ParseResult:
        frames = []
        n = len(data) // self.FRAME_SIZE
        for i in range(n):
            off = i * self.FRAME_SIZE
            # little-endian unsigned short for both
            speed_raw, temp_raw = struct.unpack_from("<HH", data, off)
            frame = {
                "idx": i,
                "speed": speed_raw * config.signal_map["speed"].scale,
                "temp": temp_raw * config.signal_map["temp"].scale,
            }
            frames.append(frame)
        return ParseResult(frames=frames, meta={"frames_parsed": len(frames)})


# PHM parser can reuse same interface; implement minimal placeholder in phm.py
