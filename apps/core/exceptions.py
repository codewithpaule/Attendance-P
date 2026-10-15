

class DomainError(Exception):
    def __init__(self, code: str, message: str, details: dict | None = None):
        self.code = code
        self.message = message
        self.details = details
        super().__init__(message)


class BadRequestError(DomainError):
    pass


class NotFoundError(DomainError):
    pass


class PermissionDeniedError(DomainError):
    pass


class ConflictError(DomainError):
    pass


class ValidationError(DomainError):
    pass
