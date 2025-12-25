class DataPipelineError(Exception):
    def __init__(self, message: str, code: str = 'UNKNOWN', retryable: bool = False):
        super().__init__(message)
        self.code = code
        self.retryable = retryable

class ConfigError(DataPipelineError):
    pass

class ParseError(DataPipelineError):
    pass