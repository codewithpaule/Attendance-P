from django.urls import path
from rest_framework.decorators import api_view
from rest_framework.response import Response

from apps.core.selectors import health_check


@api_view(["GET"])
def healthz(request):
    return Response(health_check())


urlpatterns = [
    path("healthz/", health_check, name="healthz"),
]
