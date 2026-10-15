import logging

from django.http import JsonResponse
from rest_framework.views import exception_handler

from apps.core.exceptions import DomainError

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is not None:
        return response

    if isinstance(exc, DomainError):
        logger.error(
            f"Domain error: {exc.code} - {exc.message}",
            extra={"code": exc.code, "details": exc.details},
        )
        return JsonResponse(
            {"error": {"code": exc.code, "message": exc.message, "details": exc.details or {}}},
            status=400,
        )

    logger.exception("Unhandled exception")
    return JsonResponse(
        {"error": {"code": "INTERNAL_ERROR", "message": "An unexpected error occurred"}},
        status=500,
    )
