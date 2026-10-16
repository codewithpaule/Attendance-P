from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/v1/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="docs"),
    path("api/v1/", include("apps.core.api.urls")),
    path("api/v1/", include("apps.accounts.api.urls")),
    path("api/v1/", include("apps.attendance.api.urls")),
    path("", include("apps.accounts.web.urls")),
    path("", include("apps.academics.web.urls")),
    path("", include("apps.attendance.web.urls")),
    path("", include("apps.core.api.urls")),
    path("", include("apps.ops.api.urls")),
]
