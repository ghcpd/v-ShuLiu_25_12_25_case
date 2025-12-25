# LRU-Centric Train Data Pipeline (mini-skeleton)

This repository contains a minimal skeleton demonstrating a thread-safe, namespaced LRU cache with TTL and request coalescing, simple parsers (MVB/PHM), and view wrappers. It's intended as a starting point for the full refactor described in the design brief.

Quickstart

- Create a venv and install requirements: `python -m venv .venv; .\.venv\Scripts\pip.exe install -r requirements.txt`
- Run tests: `pytest -q`

What is included

- `data_pipeline/cache/lru.py` — LRU with namespaces, TTL, and inflight coalescing
- `data_pipeline/parsers/` — placeholder parsers for MVB and PHM
- `data_pipeline/views/` — view handlers that use the cache and parsers
- `compat/legacy_api.py` — tiny compatibility wrappers
- `tests/` — tests for cache correctness and concurrency

Notes

- This is a minimal, test-focused skeleton. Many features from the full design (tiered disk cache, metrics exports, MinIO parallel fetches, async job model) are intentionally left for follow-up iterations.
