"""Minimal MinIO adapter that simulates parallel range reads for tests."""
from concurrent.futures import ThreadPoolExecutor
from typing import List


class MinioAdapter:
    def __init__(self, path: str):
        self.path = path

    def fetch_ranges(self, start_offset: int, end_offset: int, chunk_size: int = 1024) -> bytes:
        # In real system we'd do ranged HTTP requests / S3 range reads. For tests, read file.
        parts: List[bytes] = []
        with open(self.path, "rb") as f:
            f.seek(start_offset)
            to_read = end_offset - start_offset
            while to_read > 0:
                read_len = min(chunk_size, to_read)
                parts.append(f.read(read_len))
                to_read -= read_len
        return b"".join(parts)

    def parallel_fetch(self, offsets: List[tuple]) -> bytes:
        parts: List[bytes] = []
        with ThreadPoolExecutor(max_workers=min(8, len(offsets))) as exe:
            results = list(exe.map(lambda o: self.fetch_ranges(o[0], o[1]), offsets))
        return b"".join(results)
