from .base_exception import AppException

class NotFoundError(AppException):
    def __init__(self, message = "Not Found"):
        super().__init__(message, code="NOT_FOUND", status_code=404)

class InvalidInputError(AppException):
    def __init__(self, message = "Invalid Input"):
        super().__init__(message, code="INVALID_INPUT", status_code=400)

class ForbiddenError(AppException):
    def __init__(self, message = "Forbidden"):
        super().__init__(message, code="FORBIDDEN", status_code=403)

class SystemError(AppException):
    def __init__(self, message = "Internal Server Error"):
        super().__init__(message, code="SYSTEM_ERROR", status_code=500)
