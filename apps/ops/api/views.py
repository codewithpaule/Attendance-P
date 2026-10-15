
from django.http import HttpRequest, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from apps.core.exceptions import ConflictError, NotFoundError
from apps.ops.services.jobs import run_job, verify_job_secret


@require_http_methods(["POST"])
@csrf_exempt
def job_endpoint(request: HttpRequest, name: str) -> JsonResponse:
    """Execute a job by name.

    Auth: Authorization: Bearer <JOBS_SECRET>
    Returns 404 for invalid auth (does not reveal route)
    """
    # Verify secret
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return JsonResponse({"error": "Unauthorized"}, status=404)

    secret = auth_header[7:]  # Remove "Bearer " prefix
    if not verify_job_secret(secret):
        return JsonResponse({"error": "Unauthorized"}, status=404)

    # Run the job
    try:
        stats = run_job(name)
        return JsonResponse({"status": "success", "stats": stats})
    except NotFoundError as e:
        return JsonResponse({"error": e.message}, status=404)
    except ConflictError as e:
        return JsonResponse({"error": e.message}, status=409)
    except Exception:
        return JsonResponse({"error": "Internal server error"}, status=500)
