#!/usr/bin/env python
"""
Quick validation script - tests core functionality without full test suite.
"""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test that all modules import correctly."""
    print("Testing imports...")
    try:
        from data_pipeline import (
            NamespacedLRUCache,
            RequestValidator,
            Router,
            MetricsCollector,
        )
        print("✓ All modules imported successfully")
        return True
    except Exception as e:
        print(f"✗ Import failed: {e}")
        return False


def test_cache():
    """Test LRU cache basic operations."""
    print("\nTesting LRU cache...")
    try:
        from data_pipeline import NamespacedLRUCache
        
        cache = NamespacedLRUCache(max_size=10, default_ttl_seconds=3600)
        
        # Test set/get
        cache.set("mvb:plot", "key1", {"speed": 50})
        val = cache.get("mvb:plot", "key1")
        assert val == {"speed": 50}, "Cache get failed"
        
        # Test namespace isolation
        cache.set("phm:plot", "key1", {"temp": 80})
        mvb_val = cache.get("mvb:plot", "key1")
        phm_val = cache.get("phm:plot", "key1")
        assert mvb_val == {"speed": 50}, "MVB value corrupted"
        assert phm_val == {"temp": 80}, "PHM value corrupted"
        
        # Test delete
        cache.delete("mvb:plot", "key1")
        val = cache.get("mvb:plot", "key1")
        assert val is None, "Delete failed"
        
        print("✓ Cache operations work correctly")
        return True
    except Exception as e:
        print(f"✗ Cache test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_validation():
    """Test request validation."""
    print("\nTesting validation...")
    try:
        from data_pipeline import RequestValidator
        from data_pipeline.errors import ValidationError
        
        # Valid request
        RequestValidator.validate_request({
            "module": "MVB",
            "requestType": "plot",
            "configVersion": "v1",
            "timeStart": "2025-12-25T08:00:00Z",
            "timeEnd": "2025-12-25T09:00:00Z",
            "timeStep": "1s",
            "trainNo": "G1234",
            "carriage": "01",
        })
        
        # Invalid request (missing module)
        try:
            RequestValidator.validate_request({
                "requestType": "plot",
                "configVersion": "v1",
                "timeStart": "2025-12-25T08:00:00Z",
                "timeEnd": "2025-12-25T09:00:00Z",
                "timeStep": "1s",
                "trainNo": "G1234",
                "carriage": "01",
            })
            print("✗ Validation should have failed for missing module")
            return False
        except ValidationError:
            pass  # Expected
        
        print("✓ Validation works correctly")
        return True
    except Exception as e:
        print(f"✗ Validation test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_metrics():
    """Test metrics collection."""
    print("\nTesting metrics...")
    try:
        from data_pipeline import NamespacedLRUCache, MetricsCollector
        
        cache = NamespacedLRUCache(max_size=10)
        metrics = MetricsCollector.get_instance()
        metrics.cache_metrics.reset()
        
        # Generate hit/miss
        cache.set("default", "key1", "value1")
        cache.get("default", "key1")  # hit
        cache.get("default", "key2")  # miss
        
        m = metrics.cache_metrics
        assert m.total_hits == 1, f"Expected 1 hit, got {m.total_hits}"
        assert m.total_misses == 1, f"Expected 1 miss, got {m.total_misses}"
        
        hit_rate = m.get_hit_rate()
        assert 0 < hit_rate < 1, f"Expected hit_rate between 0 and 1, got {hit_rate}"
        
        print("✓ Metrics collection works correctly")
        return True
    except Exception as e:
        print(f"✗ Metrics test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_compatibility_layer():
    """Test compatibility layer."""
    print("\nTesting compatibility layer...")
    try:
        from compat import initialize, parse, get_metrics
        
        initialize(config_dir="data", cache_size=100)
        
        # This will fail because config files don't exist, but imports should work
        try:
            response = parse(
                module="MVB",
                config_version="v1",
                time_start="2025-12-25T08:00:00Z",
                time_end="2025-12-25T09:00:00Z",
                time_step="1s",
                train_no="G1234",
                carriage="01",
            )
        except Exception as e:
            # Expected - config file doesn't exist
            pass
        
        print("✓ Compatibility layer initialized correctly")
        return True
    except Exception as e:
        print(f"✗ Compatibility layer test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all validation tests."""
    print("=" * 60)
    print("Data Pipeline - Quick Validation")
    print("=" * 60)
    
    tests = [
        test_imports,
        test_cache,
        test_validation,
        test_metrics,
        test_compatibility_layer,
    ]
    
    results = []
    for test in tests:
        try:
            results.append(test())
        except Exception as e:
            print(f"✗ Test {test.__name__} crashed: {e}")
            import traceback
            traceback.print_exc()
            results.append(False)
    
    # Summary
    print("\n" + "=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("✓ All validation tests passed!")
        return 0
    else:
        print(f"✗ {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
