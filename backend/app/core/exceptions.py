class ServiceError(Exception):
    """Base exception for expected service-layer failures."""

    status_code = 500
    detail = "Internal server error"
    headers: dict[str, str] | None = None

    def __init__(self, detail: str | None = None) -> None:
        super().__init__(detail or self.detail)
        if detail is not None:
            self.detail = detail


class AuthenticationError(ServiceError):
    status_code = 401
    detail = "Invalid or expired credentials"
    headers = {"WWW-Authenticate": "Bearer"}


class InactiveAccountError(ServiceError):
    status_code = 403
    detail = "Account is inactive"


class ConflictError(ServiceError):
    status_code = 409
    detail = "Resource already exists"


class NotFoundError(ServiceError):
    status_code = 404
    detail = "Resource not found"


class PayloadTooLargeError(ServiceError):
    status_code = 413
    detail = "Uploaded file is too large"


class StorageError(ServiceError):
    status_code = 502
    detail = "File storage operation failed"
