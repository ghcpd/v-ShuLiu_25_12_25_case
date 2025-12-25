# LRU-Centric Train Data Request & Parsing (mini-skeleton)

Overview
- Namespaced, TTL-aware, thread-safe LRU cache with request coalescing.
- Minimal parsers and Views for MVB/PHM that demonstrate primary/secondary caching.
- Parallelized file adapter simulating MinIO range reads.

Quick start
1. Create venv and install deps: `python -m venv .venv; .\.venv\Scripts\activate; pip install -r requirements.txt`
2. Run tests: `pytest -q`

Design highlights
- Structured cache keys include module/endpoint/config/time-window/step/train/carriage/parseMode.
- Namespaces isolate modules (no cross-pollution).
- get_or_compute implements request coalescing so concurrent identical requests compute once.
- Secondary artifacts (plot metrics) are cached separately with a secondary key.

Files of interest
- `data_pipeline/cache/lru.py` — core LRU implementation and metrics
- `data_pipeline/views/*_view.py` — parse/plot/download interface examples
- `data_pipeline/parsers/*` — placeholder byte → frames logic
- `compat/legacy_api.py` — backward-compatible façade exposing `parse/plot/download`
- `tests/` — unit tests covering correctness, concurrency, TTL/version isolation, intermediate caching

Goals & next steps
- Add disk-tier cache and persistent snapshot support
- Integrate real MinIO range reads and retry strategies
- Add observability exporters (Prometheus/OpenTelemetry)
- Implement job endpoints (async job model) and management APIs
