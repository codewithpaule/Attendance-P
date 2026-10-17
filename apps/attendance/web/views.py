from collections import Counter

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from apps.academics.domain.policy import (
    DEFAULT_ATTENDANCE_THRESHOLD_PCT,
    DEFAULT_MIN_SESSIONS_BEFORE_WARNING,
)
from apps.academics.models import EligibilityPolicy, Enrollment
from apps.accounts.models import User
from apps.attendance.models import CheckIn, ClassSession
from apps.attendance.services.review import review_checkin
from apps.attendance.services.session import finalize_session, open_session
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
@require_http_methods(["GET", "POST"])
def teacher_session_attendance_view(request, session_id):
    if request.user.role != User.Role.TEACHER:
        return HttpResponseForbidden("Teacher access is required.")

    session = get_object_or_404(
        ClassSession.objects.select_related("course", "room"),
        id=session_id,
        teacher=request.user,
    )
    action = request.POST.get("action") if request.method == "POST" else None

    if action == "review":
        try:
            review_checkin(
                session_id=str(session.id),
                checkin_id=request.POST.get("checkin_id", ""),
                teacher=request.user,
                decision=request.POST.get("decision", ""),
                note=request.POST.get("note", ""),
                clock=DefaultClock(),
            )
            messages.success(request, "Check-in review saved.")
        except DomainError as error:
            messages.error(request, error.message)
        return redirect("teacher_session_attendance", session_id=session.id)

    if action == "finalize":
        try:
            finalize_session(str(session.id), request.user, DefaultClock())
            messages.success(request, "Attendance finalized.")
        except DomainError as error:
            messages.error(request, error.message)
        return redirect("teacher_session_attendance", session_id=session.id)

    completed_sessions = ClassSession.objects.filter(
        course=session.course,
        status__in=[ClassSession.Status.CLOSED, ClassSession.Status.FINALIZED],
    )
    completed_session_ids = list(completed_sessions.values_list("id", flat=True))
    completed_session_count = len(completed_session_ids)
    present_counts = Counter(
        CheckIn.objects.filter(
            session_id__in=completed_session_ids,
            status=CheckIn.Status.PRESENT,
        ).values_list("student_id", flat=True)
    )
    policy = EligibilityPolicy.objects.filter(course=session.course).first()
    if policy is None:
        policy = EligibilityPolicy.objects.filter(course__isnull=True).first()
    warning_threshold = (
        policy.threshold_pct if policy else DEFAULT_ATTENDANCE_THRESHOLD_PCT
    )
    min_sessions_before_warning = (
        policy.min_sessions_before_alert if policy else DEFAULT_MIN_SESSIONS_BEFORE_WARNING
    )

    enrollments = Enrollment.objects.filter(course=session.course).select_related(
        "student"
    ).order_by("student__full_name", "student__student_number")
    checkins = {
        checkin.student_id: checkin
        for checkin in CheckIn.objects.filter(session=session).select_related(
            "student", "reviewed_by"
        )
    }
    roster = []
    for enrollment in enrollments:
        checkin = checkins.get(enrollment.student_id)
        attendance_pct = (
            round(100 * present_counts[enrollment.student_id] / completed_session_count)
            if completed_session_count
            else None
        )
        if checkin:
            checkin.display_flag_reasons = [
                reason.replace("_", " ").title() for reason in checkin.flag_reasons
            ]
        roster.append(
            {
                "student": enrollment.student,
                "checkin": checkin,
                "attendance_pct": attendance_pct,
                "attendance_warning": (
                    completed_session_count >= min_sessions_before_warning
                    and attendance_pct is not None
                    and attendance_pct < warning_threshold
                ),
            }
        )

    return render(
        request,
        "attendance/teacher_attendance.html",
        {
            "session": session,
            "roster": roster,
            "present_count": sum(
                1 for row in roster if row["checkin"] and row["checkin"].status == CheckIn.Status.PRESENT
            ),
            "flagged_count": sum(
                1 for row in roster if row["checkin"] and row["checkin"].status == CheckIn.Status.FLAGGED
            ),
            "absent_count": sum(
                1 for row in roster if row["checkin"] and row["checkin"].status == CheckIn.Status.ABSENT
            ),
            "not_checked_in_count": sum(1 for row in roster if not row["checkin"]),
            "warning_count": sum(1 for row in roster if row["attendance_warning"]),
            "warning_threshold": warning_threshold,
            "completed_session_count": completed_session_count,
            "min_sessions_before_warning": min_sessions_before_warning,
        },
    )


@login_required(login_url="login")
@require_http_methods(["GET"])
def student_checkin_view(request, session_id=None):
    if request.user.role != User.Role.STUDENT:
        return HttpResponseForbidden("Student access is required.")
    return render(request, "attendance/checkin.html", {"session_id": session_id})
