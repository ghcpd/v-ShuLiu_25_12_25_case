# LRU-Centric Train Data Pipeline (mini skeleton)

Summary
- Purpose: demonstrate a namespaced, TTL-aware, concurrency-safe LRU cache and a minimal parsing pipeline for MVB/PHM with tests.
- Focus: Correct cache keys, request coalescing, intermediate caching, parallel fetch simulation, and validation.

Layout
- `data_pipeline/` — core modules (cache, parsers, views, sources, config, validators)
- `compat/` — legacy API shim: `parse()`, `plot()`, `download()` preserved
- `tests/` — unit + integration tests using `data/` sample inputs

Key design points
- Structured cache keys include semantic dimensions (module, endpointId, requestType, configVersion, time window, timeStep, train/carriage, parseMode)
- Two-tier logical caching in the View: `primary` (parsed frames) and `secondary` (plots/exports)
- Request coalescing prevents duplicate work under concurrency
- Parallelized range-reads simulated in `data_pipeline.sources.minio` for testability

Running locally (Windows PowerShell)
- ./run_tests.ps1 — creates venv, installs deps and runs tests

Files to inspect first
- `data_pipeline/cache/lru.py` — core cache implementation
- `data_pipeline/views/mvb_view.py` — example of layered caching and keys
- `tests/test_cache.py` — unit + concurrency + perf assertions

Limitations
- This is a minimal, testable skeleton (not production-ready HTTP server or real MinIO client).
- Replace simulated MinIO adapter with `minio` client for production.

