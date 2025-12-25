"""Custom exceptions for pipeline."""


class DataPipelineError(Exception):
    pass


class CacheError(DataPipelineError):
    pass


class NotFoundError(DataPipelineError):
    pass


class ValidationError(DataPipelineError):
    pass
