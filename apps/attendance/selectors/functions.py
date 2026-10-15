from apps.accounts.models import User
from apps.attendance.models import CheckIn, CheckInAttempt, ClassSession


def get_session_for_teacher(session_id: str, teacher: User) -> ClassSession | None:
    return ClassSession.objects.filter(id=session_id, teacher=teacher).first()


def get_open_session_for_course(course_id: str) -> ClassSession | None:
    return ClassSession.objects.filter(
        course_id=course_id, status=ClassSession.Status.OPEN
    ).first()


def get_checkins_for_session(session_id: str) -> list[CheckIn]:
    return list(
        CheckIn.objects.filter(session_id=session_id).select_related("student", "reviewed_by")
    )


def get_checkin_for_student(session_id: str, student: User) -> CheckIn | None:
    return CheckIn.objects.filter(session_id=session_id, student=student).first()


def get_pending_checkin_attempt(attempt_id: str) -> CheckInAttempt | None:
    return CheckInAttempt.objects.filter(
        id=attempt_id, consumed_at__isnull=True
    ).select_related("student").first()


def get_pending_checkin_attempt_for_session(session_id: str, student_id: str) -> CheckInAttempt | None:
    return CheckInAttempt.objects.filter(
        session_id=session_id, student_id=student_id, consumed_at__isnull=True
    ).first()


def get_flagged_checkins_for_session(session_id: str) -> list[CheckIn]:
    return list(
        CheckIn.objects.filter(
            session_id=session_id, status=CheckIn.Status.FLAGGED, reviewed_by__isnull=True
        ).select_related("student")
    )


def get_spot_checks_for_session(session_id: str) -> list:
    from apps.attendance.models import SpotCheck

    return list(
        SpotCheck.objects.filter(
            session_id=session_id, outcome=SpotCheck.Outcome.PENDING
        ).select_related("student")
    )
