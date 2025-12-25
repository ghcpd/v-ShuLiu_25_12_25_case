"""A test-friendly 'MinIO' adapter that supports range-sliced parallel reads against local files.

This adapter intentionally simulates network latency so tests can assert parallel speedups.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Iterable, List, Tuple
import time


def _read_range(path: Path, start: int, length: int, artificial_delay: float = 0.02) -> bytes:
    # simulate network latency per-range
    time.sleep(artificial_delay)
    with path.open("rb") as f:
        f.seek(start)
        return f.read(length)


def read_in_ranges(path: Path, ranges: Iterable[Tuple[int, int]], parallelism: int = 4, delay: float = 0.02) -> bytes:
    parts = []
    with ThreadPoolExecutor(max_workers=parallelism) as ex:
        futures = {ex.submit(_read_range, path, s, l, delay): (s, l) for s, l in ranges}
        # return assembled by start offset
        completed = []
        for fut in as_completed(futures):
            data = fut.result()
            s, l = futures[fut]
            completed.append((s, data))
    completed.sort()
    return b"".join([d for _, d in completed])


def slice_for_time_window(time_start: int, time_end: int, frame_size: int, frames_per_second: int = 1, slice_seconds: int = 10) -> List[Tuple[int, int]]:
    """Return byte (start, length) ranges for the requested time window.

    Assumptions for tests: 1 frame/second by default.
    """
    if time_end <= time_start:
        return []
    total_frames = (time_end - time_start) * frames_per_second
    frames_per_slice = max(1, slice_seconds * frames_per_second)
    ranges = []
    for i in range(0, total_frames, frames_per_slice):
        start_frame = i
        num = min(frames_per_slice, total_frames - i)
        ranges.append((start_frame * frame_size, num * frame_size))
    return ranges


def fetch_time_window(path: Path, time_start: int, time_end: int, frame_size: int = 4, parallel: bool = True, **kwargs) -> bytes:
    ranges = slice_for_time_window(time_start, time_end, frame_size, **{k: kwargs[k] for k in ("frames_per_second", "slice_seconds") if k in kwargs})
    if not ranges:
        return b""
    if parallel:
        return read_in_ranges(path, ranges, kwargs.get("parallelism", 4), kwargs.get("delay", 0.02))
    # sequential
    out = bytearray()
    for s, l in ranges:
        out.extend(_read_range(path, s, l, kwargs.get("delay", 0.02)))
    return bytes(out)
