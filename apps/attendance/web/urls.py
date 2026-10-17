from django.urls import path

from apps.attendance.web.views import (
    student_attendance_view,
    student_checkin_view,
    teacher_qr_view,
    teacher_session_attendance_view,
    teacher_sessions_view,
)

urlpatterns = [
    path("teacher/sessions/", teacher_sessions_view, name="teacher_sessions"),
    path(
        "teacher/sessions/<uuid:session_id>/attendance/",
        teacher_session_attendance_view,
        name="teacher_session_attendance",
    ),
    path("teacher/qr/<uuid:session_id>/", teacher_qr_view, name="teacher_qr"),
    path("student/attendance/", student_attendance_view, name="student_attendance"),
    path("c/<uuid:session_id>/", student_checkin_view, name="public_session_checkin"),
    path("checkin/", student_checkin_view, name="student_checkin"),
]

