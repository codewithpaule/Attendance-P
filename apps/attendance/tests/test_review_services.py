import pytest

from apps.academics.models import Course, Room, Term
from apps.accounts.models import User
from apps.attendance.models import CheckIn, ClassSession
from apps.attendance.services.review import review_checkin
from apps.core.clock import DefaultClock
from apps.core.exceptions import NotFoundError


@pytest.mark.django_db
def test_teacher_can_review_flagged_checkin():
    teacher = User.objects.create_user(
        email="teacher@example.com",
        full_name="Teacher",
        role=User.Role.TEACHER,
    )
    student = User.objects.create_user(
        email="student@example.com",
        full_name="Student Example",
        role=User.Role.STUDENT,
        student_number="S-100",
    )
    term = Term.objects.create(
        name="Term 1",
        starts_on="2026-01-01",
        ends_on="2026-06-30",
    )
    room = Room.objects.create(
        name="Room 101",
        latitude=6.5244,
        longitude=3.3792,
        radius_m=50,
    )
    course = Course.objects.create(
        code="CS101",
        title="Intro to CS",
        term=term,
        teacher=teacher,
        default_room=room,
    )
    session = ClassSession.objects.create(
        course=course,
        room=room,
        teacher=teacher,
        status=ClassSession.Status.CLOSED,
    )
    checkin = CheckIn.objects.create(
        session=session,
        student=student,
        status=CheckIn.Status.FLAGGED,
        flag_reasons=["NEW_CREDENTIAL"],
        device_hint="device",
        checked_in_at=DefaultClock().now(),
    )

    reviewed = review_checkin(
        session_id=str(session.id),
        checkin_id=str(checkin.id),
        teacher=teacher,
        decision=CheckIn.Status.PRESENT,
        note="Verified in class",
        clock=DefaultClock(),
    )

    assert reviewed.status == CheckIn.Status.PRESENT
    assert reviewed.reviewed_by == teacher
    assert reviewed.reviewed_at is not None
    assert reviewed.review_note == "Verified in class"


@pytest.mark.django_db
def test_teacher_cannot_review_another_teachers_checkin():
    teacher = User.objects.create_user(
        email="teacher@example.com",
        full_name="Teacher",
        role=User.Role.TEACHER,
    )
    other_teacher = User.objects.create_user(
        email="other@example.com",
        full_name="Other Teacher",
        role=User.Role.TEACHER,
    )
    student = User.objects.create_user(
        email="student@example.com",
        full_name="Student Example",
        role=User.Role.STUDENT,
    )
    term = Term.objects.create(
        name="Term 1",
        starts_on="2026-01-01",
        ends_on="2026-06-30",
    )
    room = Room.objects.create(
        name="Room 101",
        latitude=6.5244,
        longitude=3.3792,
        radius_m=50,
    )
    course = Course.objects.create(
        code="CS101",
        title="Intro to CS",
        term=term,
        teacher=teacher,
        default_room=room,
    )
    session = ClassSession.objects.create(
        course=course,
        room=room,
        teacher=teacher,
        status=ClassSession.Status.CLOSED,
    )
    checkin = CheckIn.objects.create(
        session=session,
        student=student,
        status=CheckIn.Status.FLAGGED,
        flag_reasons=["NEW_CREDENTIAL"],
        device_hint="device",
        checked_in_at=DefaultClock().now(),
    )

    with pytest.raises(NotFoundError):
        review_checkin(
            session_id=str(session.id),
            checkin_id=str(checkin.id),
            teacher=other_teacher,
            decision=CheckIn.Status.PRESENT,
            note="",
            clock=DefaultClock(),
        )
