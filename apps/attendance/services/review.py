from django.db import transaction

from apps.accounts.models import User
from apps.attendance.models import CheckIn
from apps.audit.services.record import record
from apps.core.clock import Clock
from apps.core.exceptions import BadRequestError, ConflictError, NotFoundError


@transaction.atomic
def review_checkin(
    session_id: str,
    checkin_id: str,
    teacher: User,
    decision: str,
    note: str,
    clock: Clock,
) -> CheckIn:
    checkin = (
        CheckIn.objects.select_for_update()
        .filter(id=checkin_id, session_id=session_id, session__teacher=teacher)
        .first()
    )
    if not checkin:
        raise NotFoundError("CHECKIN_NOT_FOUND", "Check-in not found")
    if checkin.status != CheckIn.Status.FLAGGED:
        raise ConflictError("CHECKIN_ALREADY_REVIEWED", "Only flagged check-ins need review")
    if decision not in {CheckIn.Status.PRESENT, CheckIn.Status.ABSENT}:
        raise BadRequestError("INVALID_REVIEW_DECISION", "Choose present or absent")

    checkin.status = decision
    checkin.reviewed_by = teacher
    checkin.reviewed_at = clock.now()
    checkin.review_note = note.strip()
    checkin.save(
        update_fields=["status", "reviewed_by", "reviewed_at", "review_note", "updated_at"]
    )
    record(
        actor=teacher,
        action="CHECKIN_REVIEWED",
        target_type="CheckIn",
        target_id=str(checkin.id),
        metadata={"decision": decision, "note": checkin.review_note},
    )
    return checkin


@transaction.atomic
def cancel_checkin_for_retry(
    session_id: str,
    checkin_id: str,
    teacher: User,
    note: str,
) -> None:
    checkin = (
        CheckIn.objects.select_for_update()
        .filter(id=checkin_id, session_id=session_id, session__teacher=teacher)
        .first()
    )
    if not checkin:
        raise NotFoundError("CHECKIN_NOT_FOUND", "Check-in not found")
    if checkin.status != CheckIn.Status.FLAGGED:
        raise ConflictError("CHECKIN_ALREADY_REVIEWED", "Only flagged check-ins can be canceled for retry")

    record(
        actor=teacher,
        action="CHECKIN_CANCELED_FOR_RETRY",
        target_type="CheckIn",
        target_id=str(checkin.id),
        metadata={
            "student_id": str(checkin.student_id),
            "flag_reasons": checkin.flag_reasons,
            "note": note.strip(),
        },
    )
    checkin.delete()
