# LRU-Centric Train Data Request and Parsing System

High-performance, modular, concurrent, and fault-tolerant system for processing MVB/PHM train data with advanced LRU caching.

## Overview

This system migrates a mini-program to the web backend, exposing multiple POST endpoints for requesting train data from MVB (Multifunction Vehicle Bus) and PHM (Predictive Health Monitoring) modules. It features:

- **Advanced LRU Cache**: Namespaced, structured keys, TTL support, concurrency-safe
- **Modular Architecture**: Clear separation of concerns (parsing, views, sources, routing)
- **Fault Tolerance**: Retryable errors, graceful degradation
- **Observability**: Comprehensive metrics, structured logging
- **Performance**: Request coalescing, parallel fetching, streaming processing

## Key Features

### 1. Structured Cache Keys

Cache keys include all semantic dimensions to prevent cross-request pollution:

```
module/endpointId/requestType/configVersion/timeStart/timeEnd/timeStep/trainNo/carriage/parseMode
```

Examples:
- `MVB:mvb_plot#a1b2c3d4e5f6` - MVB plot request
- `PHM:phm_download#f6e5d4c3b2a1` - PHM download request

### 2. Namespace Isolation

Separate caches per module/interface:
- `MVB:plot` - MVB plotting data
- `MVB:download` - MVB downloads
- `PHM:plot` - PHM plotting data
- etc.

Prevents data pollution across modules and request types.

### 3. TTL and Expiration

Configurable time-to-live per entry:
- Default TTL: 3600 seconds (1 hour)
- Per-entry override supported
- Automatic expiration on access
- Version/config changes invalidate caches

### 4. Concurrency Safety

- Thread-safe reads/writes with RLock
- Request coalescing: identical keys compute once
- Atomic operations
- Per-namespace locking for scalability

### 5. Metrics & Observability

- Hit/miss/eviction tracking
- Per-namespace hit rates
- Top-N hot key identification
- Eviction reason distribution
- Performance metrics (latency percentiles)

## Architecture

```
data_pipeline/
├── cache/
│   └── lru.py           # NamespacedLRUCache with TTL, concurrency, metrics
├── config/
│   └── __init__.py      # ParseConfig, ConfigManager, versioning
├── validators/
│   └── __init__.py      # RequestValidator, JobRequest
├── parsers/
│   └── __init__.py      # MVBParser, PHMParser, ParserFactory, SecondaryProcessor
├── sources/
│   └── __init__.py      # LocalFileSource, MinIOSource, ParallelFetcher
├── views/
│   └── __init__.py      # ParseView, PlotView, DownloadView, ViewFactory
├── routing/
│   └── __init__.py      # Router, AsyncJobManager
├── errors.py            # Exception hierarchy (retryable/non-retryable)
├── metrics.py           # CacheMetrics, PerformanceMetrics, MetricsCollector
├── logging_utils.py     # Structured logging, request context
└── __init__.py          # Main module exports

compat/
└── __init__.py          # Legacy API compatibility layer

tests/
└── test_pipeline.py     # Comprehensive test suite

data/
├── sample_config_v1.json
├── sample_request_cases.json
├── mvb_sample.bin
└── phm_sample.bin
```

## Usage

### Basic Usage (Compatibility Layer)

```python
from compat import initialize, parse, plot, download, get_metrics

# Initialize once
initialize(config_dir="data", cache_size=1000, default_ttl=3600)

# Parse request
response = parse(
    module="MVB",
    config_version="v1",
    time_start="2025-12-25T08:00:00Z",
    time_end="2025-12-25T09:00:00Z",
    time_step="1s",
    train_no="G1234",
    carriage="01"
)

# Check metrics
metrics = get_metrics()
print(f"Cache hit rate: {metrics['cache']['hit_rate']:.2%}")
```

### Advanced Usage (Direct API)

```python
from data_pipeline import (
    NamespacedLRUCache,
    RequestValidator,
    JobRequest,
    Router,
)

# Create cache
cache = NamespacedLRUCache(max_size=1000, default_ttl_seconds=3600)

# Create router
router = Router(cache, config_dir="data")

# Validate and dispatch request
request = {
    "module": "MVB",
    "requestType": "plot",
    "configVersion": "v1",
    "timeStart": "2025-12-25T08:00:00Z",
    "timeEnd": "2025-12-25T09:00:00Z",
    "timeStep": "1s",
    "trainNo": "G1234",
    "carriage": "01",
}

response = router.dispatch(request)
print(response)
```

### Configuration

Configs are stored in JSON files matching pattern `sample_config_{version}.json`:

```json
{
  "version": "v1",
  "module": "MVB",
  "parser_version": "1.0.0",
  "byte_order": "little",
  "parse_mode": "standard",
  "signal_map": {
    "speed": {"offset": 0, "length": 2, "scale": 0.1},
    "temp": {"offset": 2, "length": 2, "scale": 0.1}
  },
  "second_parse": {
    "plot_metrics": ["speed_avg", "temp_max"],
    "downsample": {"method": "mean", "step": 10}
  }
}
```

## Cache Operations

### Basic Get/Set

```python
cache = NamespacedLRUCache(max_size=1000)

# Set value
cache.set("mvb:plot", "key1", {"speed": 50}, ttl_seconds=3600)

# Get value
value = cache.get("mvb:plot", "key1")

# Delete
cache.delete("mvb:plot", "key1")
```

### Request Coalescing

When multiple threads request the same key simultaneously, only one computes:

```python
def slow_compute():
    time.sleep(1.0)
    return "expensive_result"

# All threads call compute_once with same key
result = cache.compute_once("mvb:plot", "key1", slow_compute)
# Computation happens once, others await
```

### Namespace Management

```python
# Clear entire namespace
cache.clear_namespace("mvb:plot")

# Clear all
cache.clear_all()

# List namespaces
namespaces = cache.get_namespaces()

# Get namespace size
size = cache.get_namespace_size("mvb:plot")
```

### Prewarming

```python
initial_data = {
    "key1": {"speed": 50},
    "key2": {"speed": 55},
}
cache.prewarm("mvb:plot", initial_data, ttl_seconds=3600)
```

## Metrics & Monitoring

```python
from data_pipeline.metrics import MetricsCollector

collector = MetricsCollector.get_instance()

# Get metrics
metrics = collector.cache_metrics
print(f"Hit rate: {metrics.get_hit_rate():.2%}")
print(f"Total evictions: {metrics.total_evictions}")
print(f"Namespace rates: {metrics.get_namespace_hit_rate('mvb:plot'):.2%}")

# Top accessed keys
top_10 = metrics.get_top_keys(10)

# Export for monitoring
export = collector.to_dict()
```

## Error Handling

All errors are classified as retryable or non-retryable:

```python
from data_pipeline.errors import DataPipelineException, ErrorCode

try:
    response = router.dispatch(request)
except DataPipelineException as e:
    if e.retryable:
        # Temporary error, can retry
        print(f"Retryable error: {e.code.value}")
    else:
        # Permanent error, don't retry
        print(f"Fatal error: {e.code.value}")
```

## Performance Targets

| Operation | Target |
|-----------|--------|
| Cold-start parsing (50k frames) | ≥ 40% lower CPU |
| Hot-path filtering (50k frames) | < 20 ms |
| Hot-path ID/slice lookups | < 1 ms |
| Parallel fetch + streaming (1h window) | < 2 s end-to-end |
| Cache hit rate (popular endpoints) | ≥ 85% |

## Testing

Run all tests:

```bash
python -m pytest tests/test_pipeline.py -v
```

Run specific test class:

```bash
python -m pytest tests/test_pipeline.py::TestCacheKeyCorrectness -v
```

Run with coverage:

```bash
python -m pytest tests/test_pipeline.py --cov=data_pipeline --cov-report=html
```

### Test Coverage

- **Key Correctness**: Pollution detection across dimensions
- **Concurrency**: Thread-safe operations, request coalescing
- **TTL/Versioning**: Expiration and config invalidation
- **Validation**: Request structure and content
- **Metrics**: Hit/miss tracking, namespace rates
- **Integration**: End-to-end pipeline

## Logging

Structured JSON logging with request context:

```python
from data_pipeline.logging_utils import setup_logging, set_request_context

setup_logging(level=logging.INFO)
set_request_context("req123", user="alice")
# All logs will include request_id and context
```

Log entries:

```json
{
  "timestamp": "2025-12-25T10:00:00.000000",
  "level": "INFO",
  "logger": "data_pipeline.cache.lru",
  "message": "Cache hit for mvb:mvb_plot#a1b2c3d4e5f6",
  "request_id": "req123",
  "function": "get"
}
```

## Data Sources

### Local Files

```python
from data_pipeline.sources import DataSourceFactory

source = DataSourceFactory.create_local_source("data/")
data = source.fetch("mvb_sample.bin")
```

### MinIO (Optional)

Requires `minio` package. Install with:

```bash
pip install minio
```

Usage:

```python
source = DataSourceFactory.create_minio_source(
    endpoint="localhost:9000",
    access_key="minioadmin",
    secret_key="minioadmin",
    bucket="train-data"
)
data = source.fetch("train123/mvb/2025-12-25.bin")
```

### Parallel Fetching

```python
fetcher = DataSourceFactory.create_parallel_fetcher(
    source,
    max_workers=4,
    segment_size=1024*1024  # 1MB segments
)
data = fetcher.fetch_parallel("large_file.bin")
segments = fetcher.fetch_segments("file.bin")
```

## API Endpoints

### Synchronous (Compatibility)

- `POST /parse` - Parse request, returns parsed signals
- `POST /plot` - Plot request, returns plot data
- `POST /download` - Download request, returns export data

Request body:

```json
{
  "module": "MVB|PHM",
  "requestType": "parse|plot|download",
  "configVersion": "v1|v2",
  "timeStart": "2025-12-25T08:00:00Z",
  "timeEnd": "2025-12-25T09:00:00Z",
  "timeStep": "1s",
  "trainNo": "G1234",
  "carriage": "01"
}
```

Response:

```json
{
  "request_id": "abc123",
  "status": "success|error",
  "data": {...},
  "error": null,
  "timestamp": "2025-12-25T10:00:00.000000"
}
```

### Asynchronous (Modern)

- `POST /jobs/parse` - Submit async parse job
- `GET /jobs/{id}` - Get job status
- `DELETE /jobs/{id}` - Cancel job

## Configuration Management

### Version Negotiation

```python
config_mgr = get_config_manager()

# Load specific version
config_v1 = config_mgr.get_config("v1")

# List available versions
versions = config_mgr.list_available_versions()
```

### Rollback Guidance

- Keep previous config versions available
- Cache key includes config version
- Configuration changes don't affect existing cached results

## Deployment

### Windows (PowerShell)

Use the provided `run_tests.ps1` script:

```powershell
.\run_tests.ps1
```

### Linux/Mac

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m pytest tests/test_pipeline.py -v
```

## Contributing

When adding new features:

1. Ensure cache keys include all semantic dimensions
2. Preserve namespace isolation
3. Add comprehensive tests
4. Update metrics/logging
5. Document error codes

## License

MIT

## Support

For issues or questions, check test cases in `tests/test_pipeline.py` for usage examples.
