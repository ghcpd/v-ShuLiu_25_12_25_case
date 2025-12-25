"""Parser abstractions."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Dict, Any, List


@dataclass
class ParseResult:
    frames: List[Dict[str, Any]]
    meta: Dict[str, Any]


class Parser:
    def parse_bytes(self, data: bytes, config) -> ParseResult:
        raise NotImplementedError

    def parse_stream(self, chunks: Iterable[bytes], config) -> ParseResult:
        # default: buffer everything
        buf = bytearray()
        for c in chunks:
            buf.extend(c)
        return self.parse_bytes(bytes(buf), config)
