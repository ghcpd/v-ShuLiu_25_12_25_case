"""PHM parser placeholder for compatibility/testing."""
from __future__ import annotations

from typing import Any
from .base import Parser, ParseResult


class PHMParser(Parser):
    def parse_bytes(self, data: bytes, config) -> ParseResult:
        # PHM format not implemented — return a synthetic result so tests can exercise namespacing
        n = max(1, len(data) // 8)
        frames = [{"idx": i, "value": i * 0.5} for i in range(n)]
        return ParseResult(frames=frames, meta={"frames_parsed": len(frames)})
