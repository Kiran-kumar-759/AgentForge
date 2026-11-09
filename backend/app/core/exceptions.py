class ORCAException(Exception):
    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)

class ConfigurationError(ORCAException):
    def __init__(self, message: str):
        super().__init__(message, status_code=500)

class DatabaseError(ORCAException):
    def __init__(self, message: str):
        super().__init__(message, status_code=500)

class CacheError(ORCAException):
    def __init__(self, message: str):
        super().__init__(message, status_code=500)

class ValidationError(ORCAException):
    def __init__(self, message: str):
        super().__init__(message, status_code=400)

class ProviderError(ORCAException):
    pass

class ProviderAuthenticationFailure(ProviderError):
    pass

class ProviderRateLimit(ProviderError):
    pass

class ProviderTimeout(ProviderError):
    pass

class ProviderUnavailable(ProviderError):
    pass

class InternalError(ORCAException):
    def __init__(self, message: str):
        super().__init__(message, status_code=500)
