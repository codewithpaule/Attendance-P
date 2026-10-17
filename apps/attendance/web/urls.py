from django.urls import path

from apps.attendance.web.views import (
    student_checkin_view,
    teacher_qr_view,
    teacher_sessions_view,
)

urlpatterns = [
    path("teacher/sessions/", teacher_sessions_view, name="teacher_sessions"),
    path("teacher/qr/<uuid:session_id>/", teacher_qr_view, name="teacher_qr"),
    path("c/<uuid:session_id>/", student_checkin_view, name="public_session_checkin"),
    path("checkin/", student_checkin_view, name="student_checkin"),
]

