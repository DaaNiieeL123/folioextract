class AppError(Exception):
    def __init__(self, message: str, code: str = "app_error", status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code


class ValidationError(AppError):
    def __init__(self, message: str):
        super().__init__(message=message, code="validation_error", status_code=422)


class InfrastructureError(AppError):
    def __init__(self, message: str):
        super().__init__(message=message, code="infrastructure_error", status_code=500)


class ConversionFailureError(AppError):
    def __init__(self, message: str):
        super().__init__(message=message, code="conversion_failed", status_code=500)


