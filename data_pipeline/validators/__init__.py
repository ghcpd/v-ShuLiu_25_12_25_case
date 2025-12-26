"""
Request validation for parsing pipeline.
"""

from typing import Dict, Any, Optional
from datetime import datetime
import re

from ..logging_utils import get_context_logger
from ..errors import ValidationError, ErrorCode

logger = get_context_logger(__name__)


class RequestValidator:
    """Validates parsing requests before processing."""
    
    SUPPORTED_MODULES = {"MVB", "PHM"}
    SUPPORTED_REQUEST_TYPES = {"plot", "download", "parse"}
    
    @staticmethod
    def validate_request(request: Dict[str, Any]) -> None:
        """
        Validate a complete parsing request.
        
        Raises ValidationError if invalid.
        """
        # Module validation
        module = request.get("module")
        if not module or module not in RequestValidator.SUPPORTED_MODULES:
            raise ValidationError(
                f"Invalid or missing module. Supported: {RequestValidator.SUPPORTED_MODULES}",
                context={"provided": module}
            )
        
        # Request type validation
        request_type = request.get("requestType")
        if not request_type or request_type not in RequestValidator.SUPPORTED_REQUEST_TYPES:
            raise ValidationError(
                f"Invalid or missing requestType. Supported: {RequestValidator.SUPPORTED_REQUEST_TYPES}",
                context={"provided": request_type}
            )
        
        # Config version validation
        config_version = request.get("configVersion")
        if not config_version:
            raise ValidationError(
                "Missing configVersion",
                context={"request": request}
            )
        
        # Time window validation
        RequestValidator.validate_time_window(
            request.get("timeStart"),
            request.get("timeEnd"),
        )
        
        # Time step validation
        time_step = request.get("timeStep")
        if not time_step:
            raise ValidationError("Missing timeStep")
        
        if not RequestValidator.validate_duration_format(time_step):
            raise ValidationError(
                f"Invalid timeStep format: {time_step}. Use format like '1s', '10m', '1h'",
                context={"provided": time_step}
            )
        
        # Train and carriage validation
        train_no = request.get("trainNo")
        carriage = request.get("carriage")
        
        if not train_no:
            raise ValidationError("Missing trainNo")
        if not carriage:
            raise ValidationError("Missing carriage")
        
        if not re.match(r"^[A-Z0-9]+$", train_no):
            raise ValidationError(f"Invalid trainNo format: {train_no}")
        
        if not re.match(r"^\d{2}$", carriage):
            raise ValidationError(f"Invalid carriage format (use 2 digits): {carriage}")
        
        logger.info(f"Request validated: module={module}, type={request_type}")
    
    @staticmethod
    def validate_time_window(time_start: Optional[str], time_end: Optional[str]) -> None:
        """
        Validate ISO 8601 time window.
        
        Raises ValidationError if invalid.
        """
        if not time_start:
            raise ValidationError("Missing timeStart")
        if not time_end:
            raise ValidationError("Missing timeEnd")
        
        try:
            start_dt = datetime.fromisoformat(time_start.replace("Z", "+00:00"))
            end_dt = datetime.fromisoformat(time_end.replace("Z", "+00:00"))
        except ValueError as e:
            raise ValidationError(
                f"Invalid ISO 8601 timestamp format: {str(e)}",
                context={"timeStart": time_start, "timeEnd": time_end}
            )
        
        if start_dt >= end_dt:
            raise ValidationError(
                "timeStart must be before timeEnd",
                context={"timeStart": time_start, "timeEnd": time_end}
            )
        
        # Check reasonable time window (not more than 1 year)
        max_duration_days = 365
        duration_days = (end_dt - start_dt).days
        if duration_days > max_duration_days:
            raise ValidationError(
                f"Time window too large: {duration_days} days (max {max_duration_days})",
                context={"duration_days": duration_days}
            )
    
    @staticmethod
    def validate_duration_format(duration_str: str) -> bool:
        """
        Validate duration format (e.g., '1s', '10m', '1h', '2d').
        
        Returns True if valid, False otherwise.
        """
        pattern = r"^\d+[smhd]$"
        return bool(re.match(pattern, duration_str.lower()))


class JobRequest:
    """Represents a job request with validated fields."""
    
    def __init__(
        self,
        job_id: str,
        module: str,
        request_type: str,
        config_version: str,
        time_start: str,
        time_end: str,
        time_step: str,
        train_no: str,
        carriage: str,
        endpoint_id: Optional[str] = None,
        parse_mode: str = "standard",
    ):
        self.job_id = job_id
        self.module = module
        self.request_type = request_type
        self.config_version = config_version
        self.time_start = time_start
        self.time_end = time_end
        self.time_step = time_step
        self.train_no = train_no
        self.carriage = carriage
        self.endpoint_id = endpoint_id or f"{module}_{request_type}"
        self.parse_mode = parse_mode
    
    @classmethod
    def from_request_dict(cls, request: Dict[str, Any]) -> "JobRequest":
        """Create from request dictionary after validation."""
        RequestValidator.validate_request(request)
        
        job_id = __import__("uuid").uuid4().hex[:12]
        
        return cls(
            job_id=job_id,
            module=request.get("module"),
            request_type=request.get("requestType"),
            config_version=request.get("configVersion"),
            time_start=request.get("timeStart"),
            time_end=request.get("timeEnd"),
            time_step=request.get("timeStep"),
            train_no=request.get("trainNo"),
            carriage=request.get("carriage"),
            endpoint_id=request.get("endpointId"),
            parse_mode=request.get("parseMode", "standard"),
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Export to dictionary."""
        return {
            "job_id": self.job_id,
            "module": self.module,
            "request_type": self.request_type,
            "config_version": self.config_version,
            "time_start": self.time_start,
            "time_end": self.time_end,
            "time_step": self.time_step,
            "train_no": self.train_no,
            "carriage": self.carriage,
            "endpoint_id": self.endpoint_id,
            "parse_mode": self.parse_mode,
        }
