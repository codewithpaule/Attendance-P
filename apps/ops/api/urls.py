from django.urls import path

from apps.ops.api.views import job_endpoint

urlpatterns = [
    path("internal/jobs/<str:name>/", job_endpoint, name="job_endpoint"),
]
