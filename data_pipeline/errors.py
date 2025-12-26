"""
Error definitions and exception hierarchy for the data pipeline.
Supports retryable/non-retryable classification and structured error codes.
"""

from enum import Enum
from typing import Optional, Any, Dict


class ErrorCode(Enum):
    """Standard error codes for the system."""
    # Retryable errors
    CACHE_MISS = "CACHE_MISS"
    TEMP_DATA_UNAVAILABLE = "TEMP_DATA_UNAVAILABLE"
    NETWORK_TIMEOUT = "NETWORK_TIMEOUT"
    RESOURCE_BUSY = "RESOURCE_BUSY"
    
    # Non-retryable errors
    INVALID_REQUEST = "INVALID_REQUEST"
    CONFIG_VERSION_NOT_FOUND = "CONFIG_VERSION_NOT_FOUND"
    PARSE_ERROR = "PARSE_ERROR"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    UNSUPPORTED_MODULE = "UNSUPPORTED_MODULE"
    UNSUPPORTED_REQUEST_TYPE = "UNSUPPORTED_REQUEST_TYPE"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    
    # System errors
    INTERNAL_ERROR = "INTERNAL_ERROR"
    NOT_IMPLEMENTED = "NOT_IMPLEMENTED"


class ErrorSeverity(Enum):
    """Error severity levels."""
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class DataPipelineException(Exception):
    """Base exception for data pipeline."""
    
    def __init__(
        self,
        code: ErrorCode,
        message: str,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        retryable: bool = False,
        context: Optional[Dict[str, Any]] = None,
    ):
        self.code = code
        self.message = message
        self.severity = severity
        self.retryable = retryable
        self.context = context or {}
        super().__init__(f"[{code.value}] {message}")


class CacheError(DataPipelineException):
    """Cache-related errors."""
    
    def __init__(self, message: str, retryable: bool = True, context: Optional[Dict[str, Any]] = None):
        super().__init__(
            ErrorCode.INTERNAL_ERROR,
            message,
            severity=ErrorSeverity.WARNING,
            retryable=retryable,
            context=context,
        )


class ConfigError(DataPipelineException):
    """Configuration validation errors."""
    
    def __init__(self, message: str, code: ErrorCode = ErrorCode.VALIDATION_ERROR):
        super().__init__(code, message, severity=ErrorSeverity.ERROR, retryable=False)


class ParsingError(DataPipelineException):
    """Parsing errors."""
    
    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        super().__init__(
            ErrorCode.PARSE_ERROR,
            message,
            severity=ErrorSeverity.ERROR,
            retryable=False,
            context=context,
        )


class ValidationError(DataPipelineException):
    """Request validation errors."""
    
    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        super().__init__(
            ErrorCode.VALIDATION_ERROR,
            message,
            severity=ErrorSeverity.ERROR,
            retryable=False,
            context=context,
        )


class DataSourceError(DataPipelineException):
    """Data source (MinIO/DB) errors."""
    
    def __init__(
        self,
        message: str,
        retryable: bool = True,
        context: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            ErrorCode.TEMP_DATA_UNAVAILABLE,
            message,
            severity=ErrorSeverity.WARNING if retryable else ErrorSeverity.ERROR,
            retryable=retryable,
            context=context,
        )


class NotImplementedError(DataPipelineException):
    """Feature not yet implemented."""
    
    def __init__(self, message: str):
        super().__init__(
            ErrorCode.NOT_IMPLEMENTED,
            message,
            severity=ErrorSeverity.WARNING,
            retryable=False,
        )
