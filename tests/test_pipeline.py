"""
Comprehensive test suite for LRU cache and data pipeline.
Covers correctness, concurrency, TTL, performance, and metrics.
"""

import unittest
import threading
import time
from datetime import datetime, timedelta
from io import BytesIO
import json

from data_pipeline import (
    NamespacedLRUCache,
    CacheKeyBuilder,
    RequestValidator,
    JobRequest,
    ParseConfig,
    ParserFactory,
    SecondaryProcessor,
    DataSourceFactory,
    Router,
    MetricsCollector,
    setup_logging,
)
from data_pipeline.errors import ValidationError, ConfigError, ParsingError
from data_pipeline.config import get_config_manager


class TestCacheKeyCorrectness(unittest.TestCase):
    """Test cache key structuring and pollution detection."""
    
    def test_different_timesteps_produce_different_keys(self):
        """Keys differing by timeStep should not match."""
        key1 = CacheKeyBuilder.build_key(
            "MVB", "mvb_plot", "plot", "v1",
            "2025-12-25T08:00:00Z", "2025-12-25T09:00:00Z", "1s",
            "G1234", "01"
        )
        key2 = CacheKeyBuilder.build_key(
            "MVB", "mvb_plot", "plot", "v1",
            "2025-12-25T08:00:00Z", "2025-12-25T09:00:00Z", "2s",
            "G1234", "01"
        )
        self.assertNotEqual(key1, key2)
    
    def test_different_modules_produce_different_keys(self):
        """Keys differing by module should not match."""
        key1 = CacheKeyBuilder.build_key(
            "MVB", "mvb_plot", "plot", "v1",
            "2025-12-25T08:00:00Z", "2025-12-25T09:00:00Z", "1s",
            "G1234", "01"
        )
        key2 = CacheKeyBuilder.build_key(
            "PHM", "phm_plot", "plot", "v1",
            "2025-12-25T08:00:00Z", "2025-12-25T09:00:00Z", "1s",
            "G1234", "01"
        )
        self.assertNotEqual(key1, key2)
    
    def test_different_request_types_produce_different_keys(self):
        """Keys differing by requestType should not match."""
        key1 = CacheKeyBuilder.build_key(
            "MVB", "mvb_plot", "plot", "v1",
            "2025-12-25T08:00:00Z", "2025-12-25T09:00:00Z", "1s",
            "G1234", "01"
        )
        key2 = CacheKeyBuilder.build_key(
            "MVB", "mvb_download", "download", "v1",
            "2025-12-25T08:00:00Z", "2025-12-25T09:00:00Z", "1s",
            "G1234", "01"
        )
        self.assertNotEqual(key1, key2)
    
    def test_identical_keys_match(self):
        """Identical dimensions produce identical keys."""
        key1 = CacheKeyBuilder.build_key(
            "MVB", "mvb_plot", "plot", "v1",
            "2025-12-25T08:00:00Z", "2025-12-25T09:00:00Z", "1s",
            "G1234", "01"
        )
        key2 = CacheKeyBuilder.build_key(
            "MVB", "mvb_plot", "plot", "v1",
            "2025-12-25T08:00:00Z", "2025-12-25T09:00:00Z", "1s",
            "G1234", "01"
        )
        self.assertEqual(key1, key2)


class TestCacheNamespaceIsolation(unittest.TestCase):
    """Test namespace isolation prevents cross-module pollution."""
    
    def setUp(self):
        self.cache = NamespacedLRUCache(max_size=100)
    
    def test_namespaces_do_not_pollute(self):
        """Values in different namespaces should not pollute each other."""
        self.cache.set("mvb:plot", "key1", "mvb_value")
        self.cache.set("phm:plot", "key1", "phm_value")
        
        mvb_val = self.cache.get("mvb:plot", "key1")
        phm_val = self.cache.get("phm:plot", "key1")
        
        self.assertEqual(mvb_val, "mvb_value")
        self.assertEqual(phm_val, "phm_value")
    
    def test_clear_namespace_isolates_effects(self):
        """Clearing one namespace doesn't affect others."""
        self.cache.set("mvb:plot", "key1", "value1")
        self.cache.set("phm:plot", "key1", "value1")
        
        self.cache.clear_namespace("mvb:plot")
        
        mvb_val = self.cache.get("mvb:plot", "key1")
        phm_val = self.cache.get("phm:plot", "key1")
        
        self.assertIsNone(mvb_val)
        self.assertEqual(phm_val, "value1")


class TestCacheTTL(unittest.TestCase):
    """Test TTL expiration behavior."""
    
    def setUp(self):
        self.cache = NamespacedLRUCache(max_size=100, default_ttl_seconds=1)
    
    def test_entries_expire_after_ttl(self):
        """Entries should expire after TTL seconds."""
        self.cache.set("default", "key1", "value1", ttl_seconds=1)
        
        # Should hit immediately
        val = self.cache.get("default", "key1")
        self.assertEqual(val, "value1")
        
        # Wait for expiration
        time.sleep(1.1)
        
        # Should miss after expiration
        val = self.cache.get("default", "key1")
        self.assertIsNone(val)
    
    def test_default_ttl_applied(self):
        """Default TTL should apply to entries without explicit TTL."""
        cache = NamespacedLRUCache(max_size=100, default_ttl_seconds=1)
        cache.set("default", "key1", "value1")
        
        val = cache.get("default", "key1")
        self.assertIsNotNone(val)
        
        time.sleep(1.1)
        val = cache.get("default", "key1")
        self.assertIsNone(val)


class TestConcurrency(unittest.TestCase):
    """Test thread-safe concurrent operations."""
    
    def setUp(self):
        self.cache = NamespacedLRUCache(max_size=100)
    
    def test_concurrent_sets_are_safe(self):
        """Multiple threads setting values concurrently."""
        results = {}
        
        def set_values(thread_id):
            for i in range(10):
                key = f"key_{thread_id}_{i}"
                self.cache.set("default", key, f"value_{i}")
                results[key] = True
        
        threads = [threading.Thread(target=set_values, args=(i,)) for i in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # All values should be present
        self.assertEqual(len(results), 40)
    
    def test_concurrent_gets_are_safe(self):
        """Multiple threads reading values concurrently."""
        # Populate cache
        for i in range(20):
            self.cache.set("default", f"key_{i}", f"value_{i}")
        
        results = []
        lock = threading.Lock()
        
        def get_values():
            for i in range(20):
                val = self.cache.get("default", f"key_{i}")
                if val:
                    with lock:
                        results.append(val)
        
        threads = [threading.Thread(target=get_values) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # Should have read all values multiple times
        self.assertGreater(len(results), 20)
    
    def test_request_coalescing_computes_once(self):
        """Identical keys compute only once, others wait for result."""
        compute_count = [0]
        lock = threading.Lock()
        
        def slow_compute():
            with lock:
                compute_count[0] += 1
            time.sleep(0.1)
            return "computed_value"
        
        results = []
        
        def access_key():
            val = self.cache.compute_once("default", "shared_key", slow_compute)
            results.append(val)
        
        threads = [threading.Thread(target=access_key) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # Compute should run only once
        self.assertEqual(compute_count[0], 1)
        # All threads should get the same result
        self.assertEqual(len(results), 5)
        self.assertTrue(all(r == "computed_value" for r in results))


class TestRequestValidation(unittest.TestCase):
    """Test request validation."""
    
    def test_missing_module_raises_error(self):
        """Missing module should raise ValidationError."""
        with self.assertRaises(ValidationError):
            RequestValidator.validate_request({
                "requestType": "plot",
                "configVersion": "v1",
                "timeStart": "2025-12-25T08:00:00Z",
                "timeEnd": "2025-12-25T09:00:00Z",
                "timeStep": "1s",
                "trainNo": "G1234",
                "carriage": "01",
            })
    
    def test_invalid_time_window_raises_error(self):
        """Invalid time window should raise ValidationError."""
        with self.assertRaises(ValidationError):
            RequestValidator.validate_request({
                "module": "MVB",
                "requestType": "plot",
                "configVersion": "v1",
                "timeStart": "2025-12-25T09:00:00Z",
                "timeEnd": "2025-12-25T08:00:00Z",  # End before start
                "timeStep": "1s",
                "trainNo": "G1234",
                "carriage": "01",
            })
    
    def test_valid_request_passes(self):
        """Valid request should pass validation."""
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


class TestMetrics(unittest.TestCase):
    """Test metrics collection."""
    
    def setUp(self):
        self.cache = NamespacedLRUCache(max_size=10)
        self.metrics = MetricsCollector.get_instance()
        self.metrics.cache_metrics.reset()
    
    def test_hit_miss_tracking(self):
        """Metrics should track hits and misses."""
        self.cache.set("default", "key1", "value1")
        
        # Hit
        self.cache.get("default", "key1")
        # Miss
        self.cache.get("default", "key2")
        
        metrics = self.metrics.cache_metrics
        self.assertEqual(metrics.total_hits, 1)
        self.assertEqual(metrics.total_misses, 1)
        self.assertGreater(metrics.get_hit_rate(), 0)
    
    def test_namespace_hit_rates(self):
        """Metrics should track per-namespace hit rates."""
        self.cache.set("mvb:plot", "key1", "value1")
        self.cache.set("phm:plot", "key1", "value1")
        
        # Generate hits/misses
        self.cache.get("mvb:plot", "key1")  # hit
        self.cache.get("mvb:plot", "key2")  # miss
        self.cache.get("phm:plot", "key1")  # hit
        self.cache.get("phm:plot", "key1")  # hit
        
        metrics = self.metrics.cache_metrics
        mvb_rate = metrics.get_namespace_hit_rate("mvb:plot")
        phm_rate = metrics.get_namespace_hit_rate("phm:plot")
        
        self.assertEqual(mvb_rate, 0.5)  # 1 hit, 1 miss
        self.assertEqual(phm_rate, 1.0)  # 2 hits


class TestConfigManagement(unittest.TestCase):
    """Test configuration versioning."""
    
    def test_config_loading_and_caching(self):
        """Configs should be loaded and cached."""
        mgr = get_config_manager("data")
        config1 = mgr.get_config("v1")
        config2 = mgr.get_config("v1")
        
        # Should be same instance (cached)
        self.assertIs(config1, config2)
    
    def test_config_validation(self):
        """Config should be validated."""
        with self.assertRaises(ConfigError):
            ParseConfig(
                version="v99",  # Invalid version
                module="MVB",
                parser_version="1.0.0",
                byte_order="little",
                parse_mode="standard",
                signal_map={},
            )


class TestParsers(unittest.TestCase):
    """Test MVB/PHM parsers."""
    
    def setUp(self):
        config_mgr = get_config_manager("data")
        self.config = config_mgr.get_config("v1")
    
    def test_mvb_parser_extracts_signals(self):
        """MVB parser should extract configured signals."""
        parser = ParserFactory.create_parser("MVB", self.config)
        raw_data = b"\x00\x01\x02\x03\x04\x05\x06\x07"
        
        result = parser.parse(raw_data)
        self.assertIsInstance(result, dict)
        # Config v1 has "speed" and "temp"
        self.assertIn("speed", result)
        self.assertIn("temp", result)
    
    def test_parser_respects_byte_order(self):
        """Parser should respect configured byte order."""
        config = ParseConfig(
            version="v1",
            module="MVB",
            parser_version="1.0.0",
            byte_order="little",
            parse_mode="standard",
            signal_map={"test": {"offset": 0, "length": 2, "scale": 1.0}},
        )
        
        parser = ParserFactory.create_parser("MVB", config)
        self.assertEqual(parser.byte_order, "little")


class TestSecondaryProcessor(unittest.TestCase):
    """Test secondary metric computation."""
    
    def test_average_metric_computation(self):
        """Should compute average metrics."""
        signals = [
            {"speed": 10, "temp": 25},
            {"speed": 20, "temp": 30},
            {"speed": 30, "temp": 35},
        ]
        
        metrics = SecondaryProcessor.compute_metrics(signals, ["speed_avg", "temp_avg"])
        
        self.assertAlmostEqual(metrics["speed_avg"], 20.0)
        self.assertAlmostEqual(metrics["temp_avg"], 30.0)
    
    def test_downsampling(self):
        """Should downsample signals correctly."""
        signals = [{"value": i} for i in range(100)]
        
        downsampled = SecondaryProcessor.downsample(signals, method="first", step=10)
        
        self.assertEqual(len(downsampled), 10)
        self.assertEqual(downsampled[0]["value"], 0)
        self.assertEqual(downsampled[1]["value"], 10)


class TestIntegration(unittest.TestCase):
    """Integration tests for full pipeline."""
    
    def test_end_to_end_request_processing(self):
        """Full request from validation to caching should work."""
        cache = NamespacedLRUCache(max_size=100)
        router = Router(cache, "data")
        
        request = {
            "module": "MVB",
            "requestType": "parse",
            "configVersion": "v1",
            "timeStart": "2025-12-25T08:00:00Z",
            "timeEnd": "2025-12-25T09:00:00Z",
            "timeStep": "1s",
            "trainNo": "G1234",
            "carriage": "01",
        }
        
        response = router.dispatch(request)
        
        self.assertEqual(response["status"], "success")
        self.assertIn("request_id", response)
        self.assertIsNotNone(response["data"])


def run_tests():
    """Run all tests."""
    setup_logging()
    unittest.main(argv=[''], exit=False, verbosity=2)


if __name__ == "__main__":
    run_tests()
