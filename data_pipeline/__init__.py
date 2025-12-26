"""
High-performance, modular data pipeline for MVB/PHM train data.
Features: LRU cache with namespaces, TTL, concurrency safety, metrics.
"""

from .cache import NamespacedLRUCache, CacheKeyBuilder
from .config import ParseConfig, ConfigManager, get_config_manager
from .validators import RequestValidator, JobRequest
from .parsers import ParserFactory, SecondaryProcessor
from .sources import DataSourceFactory, LocalFileSource, ParallelFetcher
from .views import ResponseEnvelope, BaseView, ParseView, PlotView, DownloadView, ViewFactory
from .routing import Router, AsyncJobManager
from .errors import DataPipelineException, ErrorCode, CacheError, ConfigError, ParsingError
from .metrics import CacheMetrics, PerformanceMetrics, MetricsCollector
from .logging_utils import setup_logging, get_context_logger, set_request_context

__version__ = "1.0.0"

__all__ = [
    # Cache
    "NamespacedLRUCache",
    "CacheKeyBuilder",
    # Config
    "ParseConfig",
    "ConfigManager",
    "get_config_manager",
    # Validators
    "RequestValidator",
    "JobRequest",
    # Parsers
    "ParserFactory",
    "SecondaryProcessor",
    # Sources
    "DataSourceFactory",
    "LocalFileSource",
    "ParallelFetcher",
    # Views
    "ResponseEnvelope",
    "BaseView",
    "ParseView",
    "PlotView",
    "DownloadView",
    "ViewFactory",
    # Routing
    "Router",
    "AsyncJobManager",
    # Errors
    "DataPipelineException",
    "ErrorCode",
    "CacheError",
    "ConfigError",
    "ParsingError",
    # Metrics
    "CacheMetrics",
    "PerformanceMetrics",
    "MetricsCollector",
    # Logging
    "setup_logging",
    "get_context_logger",
    "set_request_context",
]
