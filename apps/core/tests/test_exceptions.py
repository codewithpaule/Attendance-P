from apps.core.exceptions import (
    BadRequestError,
    ConflictError,
    DomainError,
    NotFoundError,
    PermissionDeniedError,
    ValidationError,
)


def test_domain_error_basic():
    error = DomainError(code="TEST", message="Test message")
    assert error.code == "TEST"
    assert error.message == "Test message"
    assert error.details is None


def test_domain_error_with_details():
    error = DomainError(code="TEST", message="Test message", details={"field": "value"})
    assert error.details == {"field": "value"}


def test_bad_request_error():
    error = BadRequestError(code="BAD_REQUEST", message="Bad request")
    assert isinstance(error, DomainError)


def test_not_found_error():
    error = NotFoundError(code="NOT_FOUND", message="Not found")
    assert isinstance(error, DomainError)


def test_permission_denied_error():
    error = PermissionDeniedError(code="PERMISSION_DENIED", message="Permission denied")
    assert isinstance(error, DomainError)


def test_conflict_error():
    error = ConflictError(code="CONFLICT", message="Conflict")
    assert isinstance(error, DomainError)


def test_validation_error():
    error = ValidationError(code="VALIDATION_ERROR", message="Validation error")
    assert isinstance(error, DomainError)
