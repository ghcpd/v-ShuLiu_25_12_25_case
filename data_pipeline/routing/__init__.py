"""
Request routing based on module and endpoint.
Maps requests to appropriate views without exposing view names in request body.
"""

from typing import Dict, Any, Optional
from ..views import ViewFactory, BaseView
from ..validators import JobRequest, RequestValidator
from ..cache import NamespacedLRUCache
from ..logging_utils import get_context_logger
from ..errors import DataPipelineException, ValidationError, ErrorCode

logger = get_context_logger(__name__)


class Router:
    """Routes requests to appropriate handler views."""
    
    def __init__(self, cache: NamespacedLRUCache, config_dir: str = "data"):
        self.cache = cache
        self.config_dir = config_dir
        self.view_factory = ViewFactory(cache, config_dir)
    
    def route_request(self, request: Dict[str, Any]) -> str:
        """
        Route a request to appropriate view.
        
        Args:
            request: Request dictionary with module, requestType, etc.
        
        Returns:
            endpointId (view identifier) based on routing rules
        """
        module = request.get("module")
        request_type = request.get("requestType")
        
        if not module or not request_type:
            raise ValidationError("Missing module or requestType")
        
        # Endpoint ID is derived from module + requestType
        endpoint_id = f"{module}_{request_type}"
        logger.debug(f"Routed to endpoint: {endpoint_id}")
        return endpoint_id
    
    def dispatch(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Dispatch a request through validation, routing, and execution.
        
        Args:
            request: Raw request dictionary
        
        Returns:
            Response dictionary
        """
        try:
            # Validate request structure
            RequestValidator.validate_request(request)
            
            # Create job request
            job_request = JobRequest.from_request_dict(request)
            
            # Route to appropriate view
            endpoint_id = self.route_request(request)
            job_request.endpoint_id = endpoint_id
            
            # Get view for request type
            view = self.view_factory.create_view(job_request.request_type)
            
            # Execute
            response = view.handle_request(job_request)
            
            logger.info(f"Request {job_request.job_id} completed with status {response.status}")
            return response.to_dict()
        
        except DataPipelineException as e:
            logger.error(f"Pipeline error: {str(e)}")
            from ..views import ResponseEnvelope
            import uuid
            response = ResponseEnvelope(
                request_id=str(uuid.uuid4()),
                status="error",
                error={
                    "code": e.code.value,
                    "message": e.message,
                    "retryable": e.retryable,
                }
            )
            return response.to_dict()
        
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            from ..views import ResponseEnvelope
            import uuid
            response = ResponseEnvelope(
                request_id=str(uuid.uuid4()),
                status="error",
                error={
                    "code": "INTERNAL_ERROR",
                    "message": str(e),
                    "retryable": False,
                }
            )
            return response.to_dict()


class AsyncJobManager:
    """Manages asynchronous job execution."""
    
    def __init__(self, router: Router):
        self.router = router
        self.jobs: Dict[str, Dict[str, Any]] = {}
        import threading
        self._lock = threading.Lock()
    
    def submit_job(self, request: Dict[str, Any]) -> str:
        """
        Submit a job for async processing.
        
        Returns:
            job_id
        """
        import uuid
        import threading
        
        job_id = str(uuid.uuid4())
        
        with self._lock:
            self.jobs[job_id] = {
                "status": "pending",
                "request": request,
                "result": None,
                "error": None,
            }
        
        # Execute in background thread
        def execute():
            try:
                result = self.router.dispatch(request)
                with self._lock:
                    self.jobs[job_id]["status"] = "completed"
                    self.jobs[job_id]["result"] = result
            except Exception as e:
                with self._lock:
                    self.jobs[job_id]["status"] = "failed"
                    self.jobs[job_id]["error"] = str(e)
        
        thread = threading.Thread(target=execute, daemon=True)
        thread.start()
        
        logger.info(f"Submitted job {job_id}")
        return job_id
    
    def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """Get job status and result."""
        with self._lock:
            job = self.jobs.get(job_id)
        
        if not job:
            return {
                "job_id": job_id,
                "status": "not_found",
            }
        
        return {
            "job_id": job_id,
            "status": job["status"],
            "result": job.get("result"),
            "error": job.get("error"),
        }
    
    def cancel_job(self, job_id: str) -> bool:
        """Cancel a job (if still pending)."""
        with self._lock:
            job = self.jobs.get(job_id)
            if not job:
                return False
            
            if job["status"] == "pending":
                job["status"] = "cancelled"
                logger.info(f"Cancelled job {job_id}")
                return True
        
        return False
