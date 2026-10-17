from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from apps.accounts.models import User
from apps.attendance.models import ClassSession
from apps.attendance.services.session import open_session
from apps.attendance.web.forms import ClassSessionForm
from apps.core.clock import DefaultClock
from apps.core.exceptions import DomainError


@login_required(login_url="login")
@require_http_methods(["GET", "POST"])
def teacher_sessions_view(request):
    if request.user.role != User.Role.TEACHER:
        return HttpResponseForbidden("Teacher access is required.")

    if request.method == "POST" and request.POST.get("action") == "open":
        session = get_object_or_404(
            ClassSession,
            id=request.POST.get("session_id"),
            teacher=request.user,
        )
        try:
            open_session(
                session_id=str(session.id),
                teacher=request.user,
                checkin_window_minutes=settings.CHECKIN_WINDOW_MINUTES,
                clock=DefaultClock(),
            )
        except DomainError as error:
            messages.error(request, error.message)
            return redirect("teacher_sessions")
        return redirect("teacher_qr", session_id=session.id)

    form = ClassSessionForm(request.POST or None, teacher=request.user)
    if (
        request.method == "POST"
        and request.POST.get("action") == "schedule"
        and form.is_valid()
    ):
        course = form.cleaned_data["course"]
        ClassSession.objects.create(
            course=course,
            room=course.default_room,
            teacher=request.user,
            scheduled_start_at=form.cleaned_data["scheduled_start_at"],
            scheduled_end_at=form.cleaned_data["scheduled_end_at"],
        )
        messages.success(request, "Class session scheduled.")
        return redirect("teacher_sessions")

    sessions = ClassSession.objects.filter(teacher=request.user).select_related(
        "course", "room"
    ).order_by("-scheduled_start_at", "-created_at")
    return render(
        request,
        "attendance/teacher_sessions.html",
        {"form": form, "sessions": sessions},
    )

@require_http_methods(["GET"])
@login_required(login_url="login")
def teacher_qr_view(request, session_id):
    if request.user.role != User.Role.TEACHER:
        return HttpResponseForbidden("Teacher access is required.")
    session = get_object_or_404(ClassSession, id=session_id, teacher=request.user)
    return render(
        request,
        "attendance/teacher_qr.html",
        {"session_id": session_id, "session": session},
    )


@login_required(login_url="login")
@require_http_methods(["GET"])
def student_checkin_view(request, session_id=None):
    if request.user.role != User.Role.STUDENT:
        return HttpResponseForbidden("Student access is required.")
    return render(request, "attendance/checkin.html", {"session_id": session_id})
