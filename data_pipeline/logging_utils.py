"""
Structured logging utilities for the data pipeline.
"""

import logging
import json
from typing import Any, Dict, Optional
from datetime import datetime
import threading

# Thread-local storage for request context
_request_context = threading.local()


class StructuredFormatter(logging.Formatter):
    """Formatter that outputs structured JSON logs."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            "timestamp": datetime.utcfromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add request context if available
        request_id = get_request_id()
        if request_id:
            log_data["request_id"] = request_id
        
        # Add extra fields if present
        if hasattr(record, "extra_fields"):
            log_data.update(record.extra_fields)
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_data)


class ContextLogger:
    """Logger with request context support."""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
    
    def info(self, message: str, **kwargs) -> None:
        """Log info with context."""
        self._log(logging.INFO, message, kwargs)
    
    def warning(self, message: str, **kwargs) -> None:
        """Log warning with context."""
        self._log(logging.WARNING, message, kwargs)
    
    def error(self, message: str, **kwargs) -> None:
        """Log error with context."""
        self._log(logging.ERROR, message, kwargs)
    
    def debug(self, message: str, **kwargs) -> None:
        """Log debug with context."""
        self._log(logging.DEBUG, message, kwargs)
    
    def _log(self, level: int, message: str, extra_fields: Dict[str, Any]) -> None:
        """Internal logging method with extra fields."""
        record = logging.LogRecord(
            name=self.logger.name,
            level=level,
            pathname="",
            lineno=0,
            msg=message,
            args=(),
            exc_info=None,
        )
        record.extra_fields = extra_fields
        self.logger.handle(record)


def setup_logging(name: str = "data_pipeline", level: int = logging.INFO) -> logging.Logger:
    """Setup structured logging."""
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Console handler with structured formatter
    handler = logging.StreamHandler()
    handler.setFormatter(StructuredFormatter())
    logger.addHandler(handler)
    
    return logger


def set_request_context(request_id: str, **kwargs) -> None:
    """Set request context for structured logging."""
    _request_context.id = request_id
    _request_context.data = kwargs


def get_request_id() -> Optional[str]:
    """Get current request ID from context."""
    return getattr(_request_context, "id", None)


def clear_request_context() -> None:
    """Clear request context."""
    if hasattr(_request_context, "id"):
        del _request_context.id
    if hasattr(_request_context, "data"):
        del _request_context.data


def get_context_logger(name: str) -> ContextLogger:
    """Get a context-aware logger."""
    return ContextLogger(name)
