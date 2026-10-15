from django.urls import path

from apps.attendance.web.views import student_checkin_view, teacher_qr_view

urlpatterns = [
    path("teacher/qr/<uuid:session_id>/", teacher_qr_view, name="teacher_qr"),
    path("checkin/", student_checkin_view, name="student_checkin"),
]

