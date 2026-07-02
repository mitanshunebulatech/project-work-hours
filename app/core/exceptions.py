"""
app/core/exceptions.py
Domain-level exceptions. Services raise these; FastAPI exception handlers
(registered in app/main.py) translate them into proper HTTP responses.
This keeps the service layer free of any HTTP/FastAPI imports (Clean Architecture).
"""


class AppError(Exception):
    """Base class for all domain exceptions."""

    status_code: int = 500
    detail: str = "An unexpected error occurred"

    def __init__(self, detail: str | None = None):
        self.detail = detail or self.detail
        super().__init__(self.detail)


class NotFoundError(AppError):
    status_code = 404
    detail = "Resource not found"


class ConflictError(AppError):
    status_code = 409
    detail = "Resource already exists"


class ValidationError(AppError):
    status_code = 422
    detail = "Validation failed"


class UnauthorizedError(AppError):
    status_code = 401
    detail = "Invalid credentials"


class ForbiddenError(AppError):
    status_code = 403
    detail = "You do not have permission to perform this action"


class BusinessRuleError(AppError):
    status_code = 400
    detail = "Business rule violation"
