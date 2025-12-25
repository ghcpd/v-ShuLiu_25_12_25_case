# LRU-Centric Train Data Request and Parsing System (MVB/PHM)

This system provides a high-performance, modular backend for requesting and parsing train data for MVB and PHM modules. It features an advanced LRU caching mechanism with namespaces, structured keys, concurrency safety, and metrics.

## Architecture

- **data_pipeline/**: Core modules for data processing.
  - **cache/**: LRU cache with namespaces and TTL.
  - **parsers/**: Abstract and concrete parsers for MVB/PHM.
  - **views/**: Interface files for different request types.
  - **sources/**: Data fetching adapters.
  - **config/**: Configuration loading.
  - **validators/**: Schema validation.
  - **routing/**: Request routing to views.
  - Infrastructure: logging, metrics, errors, plugins.

- **compat/**: Compatibility layer for legacy APIs.

## Key Features

- Structured cache keys preventing pollution.
- Concurrency-safe with request coalescing.
- Intermediate caching for primary and secondary parses.
- Parallel data fetching (placeholder).
- Streaming parsing (placeholder).
- Metrics and logging.

## Setup

1. Install dependencies: `pip install -r requirements.txt`
2. Run tests: `python -m pytest tests/`

## Usage

```python
from compat.legacy_api import parse

request = {
    "module": "MVB",
    "endpointId": "parse",
    "requestType": "parse",
    "configVersion": "v1",
    "timeStart": "2023-01-01T00:00:00Z",
    "timeEnd": "2023-01-01T01:00:00Z",
    "timeStep": 10,
    "trainNo": "T001",
    "carriage": "C1",
    "parseMode": "standard"
}

result = parse(request)
```

## Performance Targets

- Cold-start parsing (50k frames): ≥ 40% lower CPU
- Hot-path filtering (50k frames): < 20 ms
- Cache hit rate: ≥ 85%

## Cache Design

- Namespaces by module and stage (primary/secondary).
- Keys include all semantic dimensions.
- TTL and capacity configurable.
- Metrics: hits, misses, evictions per namespace.