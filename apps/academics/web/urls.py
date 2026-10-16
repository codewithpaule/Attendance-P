from django.urls import path

from apps.academics.web.views import classroom_map_view

urlpatterns = [path("teacher/classrooms/", classroom_map_view, name="classroom_map")]
