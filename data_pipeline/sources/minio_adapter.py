"""Simulated MinIO adapter that supports parallel range reads from local files.
This is a placeholder showing how parallel segment fetch would be implemented.
"""
from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List


class MinIOAdapter:
    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers

    def _read_range(self, path: str, start: int, length: int) -> bytes:
        with open(path, "rb") as f:
            f.seek(start)
            return f.read(length)

    def fetch_parallel(self, path: str, time_start: int, time_end: int, desired_chunks: int = 4) -> bytes:
        """Simulate slicing a large time-window into byte ranges and reading in parallel.
        For demo we ignore time and split file into equal chunks.
        """
        size = os.path.getsize(path)
        if size == 0:
            return b""
        chunk_size = max(1, size // desired_chunks)
        ranges: List[tuple[int, int]] = []
        for i in range(desired_chunks):
            start = i * chunk_size
            end = min(size, start + chunk_size)
            if start >= end:
                break
            ranges.append((start, end - start))
        parts = [None] * len(ranges)
        with ThreadPoolExecutor(max_workers=min(self.max_workers, len(ranges))) as ex:
            futures = {ex.submit(self._read_range, path, s, l): idx for idx, (s, l) in enumerate(ranges)}
            for fut in as_completed(futures):
                idx = futures[fut]
                parts[idx] = fut.result()
        return b"".join(parts)
