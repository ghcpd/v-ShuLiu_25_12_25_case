"""
View interfaces for plot, download, and parse operations.
Provides unified response envelopes and error handling.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from datetime import datetime
import uuid

from ..logging_utils import get_context_logger
from ..errors import DataPipelineException, ErrorCode, ErrorSeverity
from ..cache import NamespacedLRUCache
from ..parsers import ParserFactory, SecondaryProcessor
from ..config import ParseConfig
from ..validators import JobRequest

logger = get_context_logger(__name__)


@dataclass
class ResponseEnvelope:
    """Unified response format for all endpoints."""
    request_id: str
    status: str  # "success", "pending", "error"
    data: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None
    timestamp: str = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "request_id": self.request_id,
            "status": self.status,
            "data": self.data,
            "error": self.error,
            "timestamp": self.timestamp,
        }


class BaseView(ABC):
    """Abstract base for request handlers (Views)."""
    
    def __init__(self, cache: NamespacedLRUCache, config_dir: str = "data"):
        self.cache = cache
        self.config_dir = config_dir
    
    @abstractmethod
    def handle_request(self, job_request: JobRequest) -> ResponseEnvelope:
        """Process a request and return response."""
        pass
    
    def _build_namespace(self, job_request: JobRequest) -> str:
        """Build namespace from request."""
        return f"{job_request.module}:{job_request.endpoint_id}"
    
    def _build_cache_key(self, job_request: JobRequest) -> str:
        """Build cache key from request."""
        from ..cache import CacheKeyBuilder
        return CacheKeyBuilder.build_key(
            module=job_request.module,
            endpoint_id=job_request.endpoint_id,
            request_type=job_request.request_type,
            config_version=job_request.config_version,
            time_start=job_request.time_start,
            time_end=job_request.time_end,
            time_step=job_request.time_step,
            train_no=job_request.train_no,
            carriage=job_request.carriage,
            parse_mode=job_request.parse_mode,
        )
    
    def _create_error_response(
        self,
        request_id: str,
        error: Exception,
        status: str = "error",
    ) -> ResponseEnvelope:
        """Create error response from exception."""
        error_data = {
            "code": "INTERNAL_ERROR",
            "message": str(error),
        }
        
        if isinstance(error, DataPipelineException):
            error_data["code"] = error.code.value
            error_data["severity"] = error.severity.value
            error_data["retryable"] = error.retryable
            if error.context:
                error_data["context"] = error.context
        
        return ResponseEnvelope(
            request_id=request_id,
            status=status,
            error=error_data,
        )


class ParseView(BaseView):
    """Handler for parse requests."""
    
    def handle_request(self, job_request: JobRequest) -> ResponseEnvelope:
        """Process parse request."""
        logger.info(f"ParseView handling request {job_request.job_id}")
        
        request_id = job_request.job_id
        namespace = self._build_namespace(job_request)
        cache_key = self._build_cache_key(job_request)
        
        try:
            # Try cache first
            cached = self.cache.get(namespace, cache_key)
            if cached is not None:
                logger.info(f"Cache hit for {cache_key}")
                return ResponseEnvelope(
                    request_id=request_id,
                    status="success",
                    data={"cached": True, "result": cached},
                )
            
            # Load config
            from ..config import get_config_manager
            config_mgr = get_config_manager(self.config_dir)
            config = config_mgr.get_config(job_request.config_version)
            
            # Create parser
            parser = ParserFactory.create_parser(job_request.module, config)
            
            # Load data (mock for now)
            raw_data = self._load_sample_data(job_request.module)
            
            # Parse
            parsed = parser.parse(raw_data)
            
            # Apply secondary processing if configured
            result = parsed
            if config.second_parse and config.second_parse.get("plot_metrics"):
                # For single parse, wrap in list
                metrics = SecondaryProcessor.compute_metrics(
                    [parsed],
                    config.second_parse["plot_metrics"],
                )
                result = {**parsed, **metrics}
            
            # Cache result
            self.cache.set(namespace, cache_key, result, ttl_seconds=3600)
            
            return ResponseEnvelope(
                request_id=request_id,
                status="success",
                data={"cached": False, "result": result},
            )
        
        except Exception as e:
            logger.error(f"Parse error: {str(e)}")
            return self._create_error_response(request_id, e)
    
    def _load_sample_data(self, module: str) -> bytes:
        """Load sample data for testing."""
        import os
        filepath = os.path.join(self.config_dir, f"{module.lower()}_sample.bin")
        
        if os.path.exists(filepath):
            with open(filepath, "rb") as f:
                return f.read()
        
        # Return synthetic data for testing
        return b"\x00\x01\x02\x03\x04\x05\x06\x07"


class PlotView(BaseView):
    """Handler for plot rendering requests."""
    
    def handle_request(self, job_request: JobRequest) -> ResponseEnvelope:
        """Process plot request."""
        logger.info(f"PlotView handling request {job_request.job_id}")
        
        request_id = job_request.job_id
        namespace = self._build_namespace(job_request)
        cache_key = self._build_cache_key(job_request)
        
        try:
            # Try cache
            cached = self.cache.get(namespace, cache_key)
            if cached is not None:
                logger.info(f"Cache hit for {cache_key}")
                return ResponseEnvelope(
                    request_id=request_id,
                    status="success",
                    data={"cached": True, "plot_data": cached},
                )
            
            # Load config
            from ..config import get_config_manager
            config_mgr = get_config_manager(self.config_dir)
            config = config_mgr.get_config(job_request.config_version)
            
            # Parse data
            parser = ParserFactory.create_parser(job_request.module, config)
            raw_data = self._load_sample_data(job_request.module)
            parsed = parser.parse(raw_data)
            
            # Compute plot metrics
            plot_data = parsed
            if config.second_parse:
                plot_metrics = config.second_parse.get("plot_metrics", [])
                if plot_metrics:
                    metrics = SecondaryProcessor.compute_metrics([parsed], plot_metrics)
                    plot_data = {**parsed, **metrics}
                
                # Apply downsampling
                downsample_cfg = config.second_parse.get("downsample", {})
                if downsample_cfg:
                    # Mock downsampling (would normally apply to series)
                    pass
            
            # Cache
            self.cache.set(namespace, cache_key, plot_data, ttl_seconds=1800)
            
            return ResponseEnvelope(
                request_id=request_id,
                status="success",
                data={"cached": False, "plot_data": plot_data},
            )
        
        except Exception as e:
            logger.error(f"Plot error: {str(e)}")
            return self._create_error_response(request_id, e)
    
    def _load_sample_data(self, module: str) -> bytes:
        """Load sample data for testing."""
        import os
        filepath = os.path.join(self.config_dir, f"{module.lower()}_sample.bin")
        
        if os.path.exists(filepath):
            with open(filepath, "rb") as f:
                return f.read()
        
        return b"\x00\x01\x02\x03\x04\x05\x06\x07"


class DownloadView(BaseView):
    """Handler for data download requests."""
    
    def handle_request(self, job_request: JobRequest) -> ResponseEnvelope:
        """Process download request."""
        logger.info(f"DownloadView handling request {job_request.job_id}")
        
        request_id = job_request.job_id
        namespace = self._build_namespace(job_request)
        cache_key = self._build_cache_key(job_request)
        
        try:
            # Downloads usually aren't cached (or use different cache strategy)
            # but we can cache the processed data
            
            # Load config
            from ..config import get_config_manager
            config_mgr = get_config_manager(self.config_dir)
            config = config_mgr.get_config(job_request.config_version)
            
            # Parse data
            parser = ParserFactory.create_parser(job_request.module, config)
            raw_data = self._load_sample_data(job_request.module)
            parsed = parser.parse(raw_data)
            
            # Export format
            export_data = {
                "module": job_request.module,
                "train_no": job_request.train_no,
                "carriage": job_request.carriage,
                "time_start": job_request.time_start,
                "time_end": job_request.time_end,
                "signals": parsed,
            }
            
            return ResponseEnvelope(
                request_id=request_id,
                status="success",
                data={"export": export_data},
            )
        
        except Exception as e:
            logger.error(f"Download error: {str(e)}")
            return self._create_error_response(request_id, e)
    
    def _load_sample_data(self, module: str) -> bytes:
        """Load sample data for testing."""
        import os
        filepath = os.path.join(self.config_dir, f"{module.lower()}_sample.bin")
        
        if os.path.exists(filepath):
            with open(filepath, "rb") as f:
                return f.read()
        
        return b"\x00\x01\x02\x03\x04\x05\x06\x07"


class ViewFactory:
    """Factory for creating views."""
    
    def __init__(self, cache: NamespacedLRUCache, config_dir: str = "data"):
        self.cache = cache
        self.config_dir = config_dir
    
    def create_view(self, request_type: str) -> BaseView:
        """Create appropriate view for request type."""
        if request_type == "parse":
            return ParseView(self.cache, self.config_dir)
        elif request_type == "plot":
            return PlotView(self.cache, self.config_dir)
        elif request_type == "download":
            return DownloadView(self.cache, self.config_dir)
        else:
            raise ValueError(f"Unknown request type: {request_type}")
