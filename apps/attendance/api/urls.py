from django.urls import path

from apps.attendance.api.views import (
    begin_checkin_view,
    close_session_view,
    complete_checkin_view,
    extend_session_view,
    finalize_session_view,
    open_session_view,
    qr_token_view,
    reopen_session_view,
)

urlpatterns = [
    path("sessions/<uuid:session_id>/open", open_session_view, name="open_session"),
    path("sessions/<uuid:session_id>/close", close_session_view, name="close_session"),
    path("sessions/<uuid:session_id>/reopen", reopen_session_view, name="reopen_session"),
    path("sessions/<uuid:session_id>/extend", extend_session_view, name="extend_session"),
    path(
        "sessions/<uuid:session_id>/finalize",
        finalize_session_view,
        name="finalize_session",
    ),
    path("sessions/<uuid:session_id>/qr-token", qr_token_view, name="qr_token"),
    path("checkins/begin", begin_checkin_view, name="begin_checkin"),
    path("checkins/complete", complete_checkin_view, name="complete_checkin"),
]

