from collections import Counter

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from apps.academics.domain.policy import (
    DEFAULT_ATTENDANCE_THRESHOLD_PCT,
    DEFAULT_MIN_SESSIONS_BEFORE_WARNING,
    forecast_attendance,
)
from apps.academics.models import EligibilityPolicy, Enrollment
from apps.accounts.models import User
from apps.attendance.models import CheckIn, ClassSession
from apps.attendance.services.review import cancel_checkin_for_retry, review_checkin
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

    if action == "cancel_for_retry":
        try:
            cancel_checkin_for_retry(
                session_id=str(session.id),
                checkin_id=request.POST.get("checkin_id", ""),
                teacher=request.user,
                note=request.POST.get("note", ""),
            )
            messages.success(request, "Flagged check-in canceled. The student can scan again.")
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
        if checkin:
            checkin.display_flag_reasons = [
                reason.replace("_", " ").title() for reason in checkin.flag_reasons
            ]
        roster.append({"student": enrollment.student, "checkin": checkin})

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
        },
    )


@login_required(login_url="login")
@require_http_methods(["GET"])
def student_checkin_view(request, session_id=None):
    if request.user.role != User.Role.STUDENT:
        return HttpResponseForbidden("Student access is required.")
    return render(request, "attendance/checkin.html", {"session_id": session_id})


@login_required(login_url="login")
@require_http_methods(["GET"])
def student_attendance_view(request):
    if request.user.role != User.Role.STUDENT:
        return HttpResponseForbidden("Student access is required.")

    enrollments = list(
        Enrollment.objects.filter(student=request.user)
        .select_related("course", "course__term")
        .order_by("course__term__ends_on", "course__code")
    )
    course_ids = [enrollment.course_id for enrollment in enrollments]
    completed_sessions = list(
        ClassSession.objects.filter(
            course_id__in=course_ids,
            status__in=[ClassSession.Status.CLOSED, ClassSession.Status.FINALIZED],
        ).values_list("id", "course_id")
    )
    completed_session_ids = [session_id for session_id, _ in completed_sessions]
    completed_counts = Counter(course_id for _, course_id in completed_sessions)
    present_counts = {
        row["session__course_id"]: row["count"]
        for row in CheckIn.objects.filter(
            student=request.user,
            session_id__in=completed_session_ids,
            status=CheckIn.Status.PRESENT,
        )
        .values("session__course_id")
        .annotate(count=Count("id"))
    }
    policies = {
        policy.course_id: policy
        for policy in EligibilityPolicy.objects.filter(course_id__in=course_ids)
    }
    global_policy = EligibilityPolicy.objects.filter(course__isnull=True).first()

    forecasts = []
    for enrollment in enrollments:
        course = enrollment.course
        completed = completed_counts[course.id]
        policy = policies.get(course.id) or global_policy
        threshold = policy.threshold_pct if policy else DEFAULT_ATTENDANCE_THRESHOLD_PCT
        min_sessions = (
            policy.min_sessions_before_alert
            if policy
            else DEFAULT_MIN_SESSIONS_BEFORE_WARNING
        )
        planned_sessions = course.planned_sessions
        if timezone.localdate() > course.term.ends_on:
            planned_sessions = completed

        forecast = forecast_attendance(
            present_sessions=present_counts.get(course.id, 0),
            completed_sessions=completed,
            planned_sessions=planned_sessions,
            threshold_pct=threshold,
        )
        forecasts.append(
            {
                "course": course,
                "forecast": forecast,
                "threshold": threshold,
                "min_sessions": min_sessions,
                "warning_active": (
                    forecast.below_threshold and completed >= min_sessions
                ),
            }
        )

    return render(
        request,
        "attendance/student_attendance.html",
        {"forecasts": forecasts},
    )
