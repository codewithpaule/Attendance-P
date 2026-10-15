from django.db import connection
from django.http import HttpRequest, JsonResponse
from django.views.decorators.http import require_http_methods


@require_http_methods(["GET"])
def healthz(request: HttpRequest) -> JsonResponse:
    """Liveness check - no database access."""
    return JsonResponse({"status": "ok"})


@require_http_methods(["GET"])
def readyz(request: HttpRequest) -> JsonResponse:
    """Readiness check - verifies database connectivity with timeout."""
    try:
        # Use a short timeout to avoid hanging on cold starts
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            return JsonResponse({"status": "ok", "database": "connected"})
    except Exception as e:
        return JsonResponse({"status": "error", "database": "disconnected", "error": str(e)}, status=503)
