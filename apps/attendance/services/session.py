from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.attendance.adapters.qr import DjangoQRTokenAdapter
from apps.attendance.domain.state_machine import SessionStatus, can_transition
from apps.attendance.models import ClassSession
from apps.attendance.selectors.functions import get_open_session_for_course
from apps.audit.services.record import record
from apps.core.clock import Clock
from apps.core.exceptions import BadRequestError, ConflictError, NotFoundError


def close_session_if_due(session: ClassSession, current_time) -> bool:
    if (
        session.status != ClassSession.Status.OPEN
        or not session.scheduled_end_at
        or current_time < session.scheduled_end_at
    ):
        return False

    session.status = ClassSession.Status.CLOSED
    session.closed_at = session.scheduled_end_at
    session.save(update_fields=["status", "closed_at", "updated_at"])
    record(
        actor=session.teacher,
        action="SESSION_AUTO_CLOSED",
        target_type="ClassSession",
        target_id=str(session.id),
        metadata={"scheduled_end_at": session.scheduled_end_at.isoformat()},
    )
    return True


@transaction.atomic
def open_session(
    session_id: str,
    teacher: User,
    checkin_window_minutes: int,
    clock: Clock,
) -> ClassSession:
    """Open a session for check-ins."""
    session = ClassSession.objects.filter(id=session_id, teacher=teacher).first()
    if not session:
        raise NotFoundError("SESSION_NOT_FOUND", "Session not found")

    now = clock.now()
    if session.scheduled_start_at and now < session.scheduled_start_at - timedelta(
        minutes=settings.CHECKIN_PREOPEN_MINUTES
    ):
        raise BadRequestError(
            "SESSION_TOO_EARLY",
            f"Check-in can open {settings.CHECKIN_PREOPEN_MINUTES} minutes before class starts",
        )
    if session.scheduled_end_at and now >= session.scheduled_end_at:
        raise BadRequestError("CLASS_ENDED", "The scheduled class end time has passed")

    transition = can_transition(session.status, SessionStatus.OPEN)
    if not transition.is_valid:
        raise ConflictError("INVALID_TRANSITION", f"Cannot open session: {transition.reason}")

    open_session_for_course = get_open_session_for_course(str(session.course_id))
    if open_session_for_course:
        close_session_if_due(open_session_for_course, now)
        if open_session_for_course.status == ClassSession.Status.OPEN:
            raise ConflictError("SESSION_ALREADY_OPEN", "Another session is already open for this course")

    session.status = SessionStatus.OPEN
    session.opened_at = clock.now()
    session.checkin_window_minutes = checkin_window_minutes
    session.save()

    record(
        actor=teacher,
        action="SESSION_OPENED",
        target_type="ClassSession",
        target_id=str(session.id),
    )

    return session


@transaction.atomic
def reopen_session(session_id: str, teacher: User, clock: Clock) -> ClassSession:
    session = ClassSession.objects.filter(id=session_id, teacher=teacher).first()
    if not session:
        raise NotFoundError("SESSION_NOT_FOUND", "Session not found")
    if session.status != ClassSession.Status.CLOSED:
        raise ConflictError("INVALID_TRANSITION", "Only a closed session can be reopened")
    if session.scheduled_end_at and clock.now() >= session.scheduled_end_at:
        raise BadRequestError("CLASS_ENDED", "Add extra minutes before reopening this session")
    open_session_for_course = get_open_session_for_course(str(session.course_id))
    if open_session_for_course and open_session_for_course.id != session.id:
        raise ConflictError("SESSION_ALREADY_OPEN", "Another session is already open for this course")

    session.status = ClassSession.Status.OPEN
    session.opened_at = clock.now()
    session.closed_at = None
    session.save(update_fields=["status", "opened_at", "closed_at", "updated_at"])
    record(
        actor=teacher,
        action="SESSION_REOPENED",
        target_type="ClassSession",
        target_id=str(session.id),
    )
    return session


@transaction.atomic
def extend_session(
    session_id: str,
    teacher: User,
    extra_minutes: int,
    clock: Clock,
) -> ClassSession:
    session = ClassSession.objects.filter(id=session_id, teacher=teacher).first()
    if not session:
        raise NotFoundError("SESSION_NOT_FOUND", "Session not found")
    if session.status not in {ClassSession.Status.OPEN, ClassSession.Status.CLOSED}:
        raise ConflictError("INVALID_TRANSITION", "Only an open or closed session can be extended")
    if not 1 <= extra_minutes <= 120:
        raise BadRequestError("INVALID_EXTENSION", "Extra time must be between 1 and 120 minutes")

    now = clock.now()
    base_end = session.scheduled_end_at or now
    if base_end < now:
        base_end = now
    session.scheduled_end_at = base_end + timedelta(minutes=extra_minutes)
    if session.status == ClassSession.Status.CLOSED:
        open_session_for_course = get_open_session_for_course(str(session.course_id))
        if open_session_for_course and open_session_for_course.id != session.id:
            raise ConflictError("SESSION_ALREADY_OPEN", "Another session is already open for this course")
        session.status = ClassSession.Status.OPEN
        session.opened_at = now
        session.closed_at = None
    session.save(
        update_fields=["scheduled_end_at", "status", "opened_at", "closed_at", "updated_at"]
    )
    record(
        actor=teacher,
        action="SESSION_EXTENDED",
        target_type="ClassSession",
        target_id=str(session.id),
        metadata={"extra_minutes": extra_minutes, "scheduled_end_at": session.scheduled_end_at.isoformat()},
    )
    return session


@transaction.atomic
def close_session(
    session_id: str,
    teacher: User,
    headcount: int,
    clock: Clock,
) -> ClassSession:
    """Close a session and record headcount."""
    session = ClassSession.objects.filter(id=session_id, teacher=teacher).first()
    if not session:
        raise NotFoundError("SESSION_NOT_FOUND", "Session not found")

    transition = can_transition(session.status, SessionStatus.CLOSED)
    if not transition.is_valid:
        raise ConflictError("INVALID_TRANSITION", f"Cannot close session: {transition.reason}")

    session.status = SessionStatus.CLOSED
    session.closed_at = clock.now()
    session.headcount = headcount
    session.save()

    record(
        actor=teacher,
        action="SESSION_CLOSED",
        target_type="ClassSession",
        target_id=str(session.id),
        metadata={"headcount": headcount},
    )

    return session


@transaction.atomic
def finalize_session(session_id: str, teacher: User, clock: Clock) -> ClassSession:
    """Finalize a session (all flagged check-ins resolved)."""
    from apps.attendance.selectors.functions import (
        get_flagged_checkins_for_session,
        get_spot_checks_for_session,
    )

    session = ClassSession.objects.filter(id=session_id, teacher=teacher).first()
    if not session:
        raise NotFoundError("SESSION_NOT_FOUND", "Session not found")

    transition = can_transition(session.status, SessionStatus.FINALIZED)
    if not transition.is_valid:
        raise ConflictError("INVALID_TRANSITION", f"Cannot finalize session: {transition.reason}")

    flagged = get_flagged_checkins_for_session(session_id)
    pending_spot_checks = get_spot_checks_for_session(session_id)

    if flagged or pending_spot_checks:
        raise ConflictError("PENDING_REVIEWS", "Cannot finalize: pending reviews or spot checks")

    session.status = SessionStatus.FINALIZED
    session.finalized_at = clock.now()
    session.save()

    record(
        actor=teacher,
        action="SESSION_FINALIZED",
        target_type="ClassSession",
        target_id=str(session.id),
    )

    return session


def generate_qr_token(session_id: str, teacher: User, max_age_seconds: int) -> str:
    """Generate a QR token for a session."""
    session = ClassSession.objects.filter(id=session_id, teacher=teacher).first()
    if not session:
        raise NotFoundError("SESSION_NOT_FOUND", "Session not found")

    now = timezone.now()
    close_session_if_due(session, now)
    if session.status != SessionStatus.OPEN:
        raise BadRequestError("SESSION_NOT_OPEN", "Session is not open")

    if session.scheduled_start_at and now < session.scheduled_start_at - timedelta(
        minutes=settings.CHECKIN_PREOPEN_MINUTES
    ):
        raise BadRequestError("SESSION_TOO_EARLY", "The check-in window has not opened")
    if session.scheduled_end_at and now >= session.scheduled_end_at:
        raise BadRequestError("CLASS_ENDED", "The scheduled class end time has passed")

    adapter = DjangoQRTokenAdapter(max_age_seconds=max_age_seconds)
    return adapter.generate_token(session_id)
