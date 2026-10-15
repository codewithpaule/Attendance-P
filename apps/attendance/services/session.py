from django.db import transaction

from apps.accounts.models import User
from apps.attendance.adapters.qr import DjangoQRTokenAdapter
from apps.attendance.domain.state_machine import SessionStatus, can_transition
from apps.attendance.models import ClassSession
from apps.attendance.selectors.functions import get_open_session_for_course
from apps.audit.services.record import record
from apps.core.clock import Clock
from apps.core.exceptions import BadRequestError, ConflictError, NotFoundError


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

    transition = can_transition(session.status, SessionStatus.OPEN)
    if not transition.is_valid:
        raise ConflictError("INVALID_TRANSITION", f"Cannot open session: {transition.reason}")

    open_session_for_course = get_open_session_for_course(str(session.course_id))
    if open_session_for_course:
        raise ConflictError(
            "SESSION_ALREADY_OPEN",
            "Another session is already open for this course",
        )

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

    if session.status != SessionStatus.OPEN:
        raise BadRequestError("SESSION_NOT_OPEN", "Session is not open")

    adapter = DjangoQRTokenAdapter(max_age_seconds=max_age_seconds)
    return adapter.generate_token(session_id)
