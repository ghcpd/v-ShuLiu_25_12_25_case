# LRU-Centric Train Data Processing System - START HERE

## 📋 Quick Navigation

### For New Users
1. **Start here**: Read [README.md](README.md) for overview and features
2. **Try it**: Run `python quick_test.py` for 5-test validation
3. **Run tests**: Execute `.\run_tests.ps1` (Windows) for full validation

### For Developers
1. **Architecture**: See [README.md - Architecture](README.md#architecture) section
2. **API Usage**: Check [README.md - Usage](README.md#usage) examples
3. **Code**: Explore `data_pipeline/` modules
4. **Tests**: Run `pytest tests/test_pipeline.py -v`

### For Project Managers
1. **Status**: Check [DELIVERY_CHECKLIST.md](DELIVERY_CHECKLIST.md)
2. **Summary**: Read [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)
3. **Metrics**: See test results in `IMPLEMENTATION_SUMMARY.md`

---

## 🚀 Quick Start (60 seconds)

### Option 1: Windows PowerShell (One-Click)
```powershell
.\run_tests.ps1
```
✓ Creates venv  
✓ Installs dependencies  
✓ Runs all tests  
✓ Displays metrics  

### Option 2: Quick Validation (Python)
```bash
python quick_test.py
```
Runs 5 essential tests in ~5 seconds.

### Option 3: Use Directly
```python
from compat import initialize, parse

# One-time setup
initialize(config_dir="data")

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
print(response)
```

---

## 📁 Project Structure

```
.
├── README.md                     (2,200+ lines - MAIN DOCUMENTATION)
├── IMPLEMENTATION_SUMMARY.md     (Project completion summary)
├── DELIVERY_CHECKLIST.md         (All deliverables verified)
├── START_HERE.md                 (You are here)
│
├── quick_test.py                 (5 quick validation tests)
├── run_tests.ps1                 (Windows one-click runner)
├── requirements.txt              (Python dependencies)
│
├── data_pipeline/                (Core module - 14 submodules)
│   ├── __init__.py               (Main exports)
│   ├── errors.py                 (Exception hierarchy)
│   ├── metrics.py                (Metrics collection)
│   ├── logging_utils.py          (Structured logging)
│   ├── cache/
│   │   ├── __init__.py
│   │   └── lru.py                (Main LRU cache impl)
│   ├── config/
│   │   └── __init__.py           (Configuration mgmt)
│   ├── validators/
│   │   └── __init__.py           (Request validation)
│   ├── parsers/
│   │   └── __init__.py           (MVB/PHM parsers)
│   ├── sources/
│   │   └── __init__.py           (Data adapters)
│   ├── views/
│   │   └── __init__.py           (Request handlers)
│   └── routing/
│       └── __init__.py           (Router)
│
├── compat/
│   └── __init__.py               (Legacy API compat)
│
├── tests/
│   └── test_pipeline.py          (23 unit tests)
│
└── data/
    ├── sample_config_v1.json     (Config v1)
    ├── sample_config_v2.json     (Config v2)
    ├── sample_request_cases.json (Test cases)
    ├── mvb_sample.bin            (Sample data)
    └── phm_sample.bin            (Sample data)
```

---

## ✨ Key Features

### 🎯 Structured Cache Keys
Prevents cross-request pollution across:
- Modules (MVB, PHM)
- Endpoint types (plot, download, parse)
- Config versions (v1, v2)
- Time windows, train numbers, carriages, parse modes

### 🔐 Namespace Isolation
Separate caches per view interface:
```python
cache.set("mvb:plot", key1, value1)      # MVB plot namespace
cache.set("mvb:download", key1, value2)  # MVB download namespace
cache.set("phm:plot", key1, value3)      # PHM plot namespace
```

### ⏱️ TTL & Expiration
- Default 1-hour TTL
- Per-entry override support
- Automatic cleanup on access
- Config version changes invalidate caches

### 🔄 Thread-Safe Concurrency
- Identical keys compute once
- Other requests wait for result (coalescing)
- Per-namespace locking for scalability

### 📊 Comprehensive Metrics
- Hit/miss/eviction tracking
- Per-namespace hit rates
- Top-N hot key identification
- Performance percentiles (p95, p99)

### 📝 Structured Logging
JSON-formatted logs with request context:
```json
{
  "timestamp": "2025-12-25T10:00:00",
  "level": "INFO",
  "message": "Cache hit for mvb:mvb_plot#abc123",
  "request_id": "req-789",
  "function": "get"
}
```

---

## 📊 Test Coverage

| Category | Tests | Status |
|----------|-------|--------|
| Key Correctness | 4 | ✅ |
| Concurrency | 3 | ✅ |
| TTL/Versioning | 2 | ✅ |
| Validation | 3 | ✅ |
| Metrics | 2 | ✅ |
| Config | 2 | ✅ |
| Parsers | 2 | ✅ |
| Secondary Processing | 2 | ✅ |
| Integration | 1 | ✅ |
| **TOTAL** | **23** | **✅ ALL PASS** |

Quick validation tests: **5/5 pass**

---

## 💻 System Requirements

- **Python**: 3.9+
- **OS**: Windows, Linux, macOS
- **Dependencies**: Minimal (see requirements.txt)
- **Optional**: minio (for MinIO support)

---

## 🎓 Usage Patterns

### Pattern 1: Compatibility Layer (Legacy)
```python
from compat import initialize, parse, plot, download, get_metrics

initialize()
response = parse(...)
metrics = get_metrics()
```

### Pattern 2: Direct API (Modern)
```python
from data_pipeline import NamespacedLRUCache, Router

cache = NamespacedLRUCache(max_size=1000)
router = Router(cache)
response = router.dispatch(request_dict)
```

### Pattern 3: Custom Workflow
```python
from data_pipeline import RequestValidator, ParserFactory, SecondaryProcessor

RequestValidator.validate_request(request)
parser = ParserFactory.create_parser("MVB", config)
parsed = parser.parse(raw_data)
metrics = SecondaryProcessor.compute_metrics([parsed], ["speed_avg"])
```

---

## 🚨 Error Handling

All errors are categorized as:

### Retryable
- Network timeouts
- Temporary resource unavailability
- Connection failures

### Non-Retryable  
- Invalid requests
- Missing configurations
- Unsupported modules
- Parse errors

Access error details:
```python
try:
    response = router.dispatch(request)
except DataPipelineException as e:
    print(f"Code: {e.code.value}")
    print(f"Retryable: {e.retryable}")
    print(f"Message: {e.message}")
```

---

## 🔍 Monitoring & Metrics

### Get Current Metrics
```python
from data_pipeline.metrics import MetricsCollector

collector = MetricsCollector.get_instance()
metrics = collector.to_dict()

print(f"Hit Rate: {metrics['cache']['hit_rate']:.2%}")
print(f"Hot Keys: {metrics['cache']['top_10_keys']}")
print(f"Namespace Rates: {metrics['cache']['namespace_hit_rates']}")
```

### Performance Metrics
```python
perf = metrics['performance']
for operation, stats in perf.items():
    print(f"{operation}:")
    print(f"  Avg: {stats['avg_ms']:.2f}ms")
    print(f"  P95: {stats['p95_ms']:.2f}ms")
```

---

## 📚 Documentation Map

| Document | Purpose | Audience |
|----------|---------|----------|
| [README.md](README.md) | Feature guide & API reference | Developers, DevOps |
| [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md) | Delivery summary & architecture | Managers, Architects |
| [DELIVERY_CHECKLIST.md](DELIVERY_CHECKLIST.md) | All deliverables verification | QA, Project Managers |
| [START_HERE.md](START_HERE.md) | Quick start guide | Everyone |

---

## ✅ Validation & Testing

### Run All Tests
```bash
python -m pytest tests/test_pipeline.py -v
```

### Quick Validation (5 tests)
```bash
python quick_test.py
```

### Windows One-Click
```powershell
.\run_tests.ps1
```

### Expected Output
```
✓ Imports successful
✓ Cache operations work correctly
✓ Validation works correctly
✓ Metrics collection works correctly
✓ Compatibility layer initialized correctly

Results: 5/5 tests passed ✓
```

---

## 🎯 Next Steps

1. **Understand**: Read [README.md](README.md) for comprehensive overview
2. **Validate**: Run `python quick_test.py` to verify installation
3. **Explore**: Check examples in [README.md - Usage](README.md#usage)
4. **Integrate**: Use compatibility layer for quick adoption
5. **Monitor**: Set up metrics collection for production
6. **Scale**: Review [README.md - Performance](README.md#performance-targets)

---

## 🆘 Troubleshooting

### Issue: Import errors
**Solution**: Run `python quick_test.py` to diagnose

### Issue: Config file not found
**Solution**: Ensure `data/sample_config_v1.json` exists

### Issue: Tests fail on macOS/Linux
**Solution**: Use `python -m pytest` instead of `.ps1` script

### Issue: MinIO operations fail
**Solution**: Either install minio (`pip install minio`) or use LocalFileSource

---

## 📞 Support Resources

- **Code Examples**: [README.md - Usage](README.md#usage)
- **API Reference**: [README.md - Cache Operations](README.md#cache-operations)
- **Test Cases**: [tests/test_pipeline.py](tests/test_pipeline.py)
- **Error Codes**: [data_pipeline/errors.py](data_pipeline/errors.py)

---

## 📌 Key Points to Remember

✅ Cache keys include ALL semantic dimensions  
✅ Namespaces prevent cross-module pollution  
✅ TTL prevents stale data  
✅ Thread-safe with request coalescing  
✅ Comprehensive metrics for monitoring  
✅ Structured error handling  
✅ 23 tests covering all scenarios  
✅ Production-ready code  

---

**Project Status**: ✅ **COMPLETE & VALIDATED**

Ready for integration and production deployment.

---

*Last Updated: December 25, 2025*  
*Implementation: 100% Complete*
