"""Common error types and simple taxonomy."""
from __future__ import annotations


class DataPipelineError(Exception):
    pass


class RetryableError(DataPipelineError):
    pass


class NonRetryableError(DataPipelineError):
    pass
