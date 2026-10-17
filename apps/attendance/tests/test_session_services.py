from datetime import timedelta

import pytest
from django.utils import timezone

from apps.academics.models import Course, Room, Term
from apps.accounts.models import User
from apps.attendance.models import ClassSession
from apps.attendance.services.session import (
    close_session,
    extend_session,
    finalize_session,
    generate_qr_token,
    open_session,
    reopen_session,
)
from apps.core.clock import DefaultClock
from apps.core.exceptions import BadRequestError, ConflictError, NotFoundError


class FrozenClock:
    def __init__(self, current_time):
        self.current_time = current_time

    def now(self):
        return self.current_time


@pytest.mark.django_db
def test_open_session_success():
    """Test opening a session successfully."""
    term = Term.objects.create(name="Term 1", starts_on="2024-01-01", ends_on="2024-06-30", is_current=True)
    room = Room.objects.create(name="Room 101", latitude=6.5244, longitude=3.3792, radius_m=50)
    teacher = User.objects.create_user(email="teacher@example.com", full_name="Teacher", role="teacher")
    course = Course.objects.create(code="CS101", title="Intro to CS", term=term, teacher=teacher, default_room=room)

    session = ClassSession.objects.create(course=course, room=room, teacher=teacher, status=ClassSession.Status.SCHEDULED)

    clock = DefaultClock()
    opened_session = open_session(
        session_id=str(session.id),
        teacher=teacher,
        checkin_window_minutes=15,
        clock=clock,
    )

    assert opened_session.status == ClassSession.Status.OPEN
    assert opened_session.opened_at is not None
    assert opened_session.checkin_window_minutes == 15


@pytest.mark.django_db
def test_open_session_is_allowed_exactly_20_minutes_before_start():
    term = Term.objects.create(name="Term 1", starts_on="2024-01-01", ends_on="2024-06-30", is_current=True)
    room = Room.objects.create(name="Room 101", latitude=6.5244, longitude=3.3792, radius_m=50)
    teacher = User.objects.create_user(email="teacher@example.com", full_name="Teacher", role="teacher")
    course = Course.objects.create(code="CS101", title="Intro to CS", term=term, teacher=teacher, default_room=room)
    now = timezone.now()
    session = ClassSession.objects.create(
        course=course,
        room=room,
        teacher=teacher,
        scheduled_start_at=now + timedelta(minutes=20),
        scheduled_end_at=now + timedelta(hours=1),
    )

    opened = open_session(str(session.id), teacher, 15, FrozenClock(now))

    assert opened.status == ClassSession.Status.OPEN


@pytest.mark.django_db
def test_open_session_is_rejected_more_than_20_minutes_early():
    term = Term.objects.create(name="Term 1", starts_on="2024-01-01", ends_on="2024-06-30", is_current=True)
    room = Room.objects.create(name="Room 101", latitude=6.5244, longitude=3.3792, radius_m=50)
    teacher = User.objects.create_user(email="teacher@example.com", full_name="Teacher", role="teacher")
    course = Course.objects.create(code="CS101", title="Intro to CS", term=term, teacher=teacher, default_room=room)
    now = timezone.now()
    session = ClassSession.objects.create(
        course=course,
        room=room,
        teacher=teacher,
        scheduled_start_at=now + timedelta(minutes=21),
        scheduled_end_at=now + timedelta(hours=1),
    )

    with pytest.raises(BadRequestError, match="20 minutes before"):
        open_session(str(session.id), teacher, 15, FrozenClock(now))


@pytest.mark.django_db
def test_teacher_can_extend_closed_session_and_reopen_scanning():
    term = Term.objects.create(name="Term 1", starts_on="2024-01-01", ends_on="2024-06-30", is_current=True)
    room = Room.objects.create(name="Room 101", latitude=6.5244, longitude=3.3792, radius_m=50)
    teacher = User.objects.create_user(email="teacher@example.com", full_name="Teacher", role="teacher")
    other_teacher = User.objects.create_user(email="other@example.com", full_name="Other", role="teacher")
    course = Course.objects.create(code="CS101", title="Intro to CS", term=term, teacher=teacher, default_room=room)
    now = timezone.now()
    session = ClassSession.objects.create(
        course=course,
        room=room,
        teacher=teacher,
        status=ClassSession.Status.CLOSED,
        scheduled_end_at=now - timedelta(minutes=5),
    )

    extended = extend_session(str(session.id), teacher, 10, FrozenClock(now))

    assert extended.status == ClassSession.Status.OPEN
    assert extended.scheduled_end_at == now + timedelta(minutes=10)
    with pytest.raises(NotFoundError):
        extend_session(str(session.id), other_teacher, 10, FrozenClock(now))


@pytest.mark.django_db
def test_teacher_can_reopen_closed_session_before_scheduled_end():
    term = Term.objects.create(name="Term 1", starts_on="2024-01-01", ends_on="2024-06-30", is_current=True)
    room = Room.objects.create(name="Room 101", latitude=6.5244, longitude=3.3792, radius_m=50)
    teacher = User.objects.create_user(email="teacher@example.com", full_name="Teacher", role="teacher")
    course = Course.objects.create(code="CS101", title="Intro to CS", term=term, teacher=teacher, default_room=room)
    now = timezone.now()
    session = ClassSession.objects.create(
        course=course,
        room=room,
        teacher=teacher,
        status=ClassSession.Status.CLOSED,
        scheduled_end_at=now + timedelta(minutes=5),
    )

    reopened = reopen_session(str(session.id), teacher, FrozenClock(now))

    assert reopened.status == ClassSession.Status.OPEN
    assert reopened.closed_at is None


@pytest.mark.django_db
def test_open_session_twice_fails():
    """Test opening a session twice fails."""
    term = Term.objects.create(name="Term 1", starts_on="2024-01-01", ends_on="2024-06-30", is_current=True)
    room = Room.objects.create(name="Room 101", latitude=6.5244, longitude=3.3792, radius_m=50)
    teacher = User.objects.create_user(email="teacher@example.com", full_name="Teacher", role="teacher")
    course = Course.objects.create(code="CS101", title="Intro to CS", term=term, teacher=teacher, default_room=room)

    session = ClassSession.objects.create(course=course, room=room, teacher=teacher, status=ClassSession.Status.OPEN)

    clock = DefaultClock()

    with pytest.raises(ConflictError):
        open_session(
            session_id=str(session.id),
            teacher=teacher,
            checkin_window_minutes=15,
            clock=clock,
        )


@pytest.mark.django_db
def test_open_session_another_open_for_course_fails():
    """Test opening a session when another is already open for the same course."""
    term = Term.objects.create(name="Term 1", starts_on="2024-01-01", ends_on="2024-06-30", is_current=True)
    room = Room.objects.create(name="Room 101", latitude=6.5244, longitude=3.3792, radius_m=50)
    teacher = User.objects.create_user(email="teacher@example.com", full_name="Teacher", role="teacher")
    course = Course.objects.create(code="CS101", title="Intro to CS", term=term, teacher=teacher, default_room=room)

    ClassSession.objects.create(course=course, room=room, teacher=teacher, status=ClassSession.Status.OPEN)
    scheduled_session = ClassSession.objects.create(course=course, room=room, teacher=teacher, status=ClassSession.Status.SCHEDULED)

    clock = DefaultClock()

    with pytest.raises(ConflictError, match="Another session is already open"):
        open_session(
            session_id=str(scheduled_session.id),
            teacher=teacher,
            checkin_window_minutes=15,
            clock=clock,
        )


@pytest.mark.django_db
def test_open_session_not_owner_fails():
    """Test opening a session by non-owner fails."""
    term = Term.objects.create(name="Term 1", starts_on="2024-01-01", ends_on="2024-06-30", is_current=True)
    room = Room.objects.create(name="Room 101", latitude=6.5244, longitude=3.3792, radius_m=50)
    teacher = User.objects.create_user(email="teacher@example.com", full_name="Teacher", role="teacher")
    other_teacher = User.objects.create_user(email="other@example.com", full_name="Other", role="teacher")
    course = Course.objects.create(code="CS101", title="Intro to CS", term=term, teacher=teacher, default_room=room)

    session = ClassSession.objects.create(course=course, room=room, teacher=teacher, status=ClassSession.Status.SCHEDULED)

    clock = DefaultClock()

    with pytest.raises(NotFoundError):
        open_session(
            session_id=str(session.id),
            teacher=other_teacher,
            checkin_window_minutes=15,
            clock=clock,
        )


@pytest.mark.django_db
def test_close_session_success():
    """Test closing a session successfully."""
    term = Term.objects.create(name="Term 1", starts_on="2024-01-01", ends_on="2024-06-30", is_current=True)
    room = Room.objects.create(name="Room 101", latitude=6.5244, longitude=3.3792, radius_m=50)
    teacher = User.objects.create_user(email="teacher@example.com", full_name="Teacher", role="teacher")
    course = Course.objects.create(code="CS101", title="Intro to CS", term=term, teacher=teacher, default_room=room)

    session = ClassSession.objects.create(course=course, room=room, teacher=teacher, status=ClassSession.Status.OPEN)

    clock = DefaultClock()
    closed_session = close_session(
        session_id=str(session.id),
        teacher=teacher,
        headcount=30,
        clock=clock,
    )

    assert closed_session.status == ClassSession.Status.CLOSED
    assert closed_session.closed_at is not None
    assert closed_session.headcount == 30


@pytest.mark.django_db
def test_close_session_already_closed_fails():
    """Test closing an already closed session fails."""
    term = Term.objects.create(name="Term 1", starts_on="2024-01-01", ends_on="2024-06-30", is_current=True)
    room = Room.objects.create(name="Room 101", latitude=6.5244, longitude=3.3792, radius_m=50)
    teacher = User.objects.create_user(email="teacher@example.com", full_name="Teacher", role="teacher")
    course = Course.objects.create(code="CS101", title="Intro to CS", term=term, teacher=teacher, default_room=room)

    session = ClassSession.objects.create(course=course, room=room, teacher=teacher, status=ClassSession.Status.CLOSED)

    clock = DefaultClock()

    with pytest.raises(ConflictError):
        close_session(
            session_id=str(session.id),
            teacher=teacher,
            headcount=30,
            clock=clock,
        )


@pytest.mark.django_db
def test_finalize_session_success():
    """Test finalizing a session successfully."""
    term = Term.objects.create(name="Term 1", starts_on="2024-01-01", ends_on="2024-06-30", is_current=True)
    room = Room.objects.create(name="Room 101", latitude=6.5244, longitude=3.3792, radius_m=50)
    teacher = User.objects.create_user(email="teacher@example.com", full_name="Teacher", role="teacher")
    course = Course.objects.create(code="CS101", title="Intro to CS", term=term, teacher=teacher, default_room=room)

    session = ClassSession.objects.create(course=course, room=room, teacher=teacher, status=ClassSession.Status.CLOSED)

    clock = DefaultClock()
    finalized_session = finalize_session(
        session_id=str(session.id),
        teacher=teacher,
        clock=clock,
    )

    assert finalized_session.status == ClassSession.Status.FINALIZED
    assert finalized_session.finalized_at is not None


@pytest.mark.django_db
def test_finalize_session_with_flagged_checkins_fails():
    """Test finalizing a session with flagged check-ins fails."""
    term = Term.objects.create(name="Term 1", starts_on="2024-01-01", ends_on="2024-06-30", is_current=True)
    room = Room.objects.create(name="Room 101", latitude=6.5244, longitude=3.3792, radius_m=50)
    teacher = User.objects.create_user(email="teacher@example.com", full_name="Teacher", role="teacher")
    student = User.objects.create_user(email="student@example.com", full_name="Student", role="student")
    course = Course.objects.create(code="CS101", title="Intro to CS", term=term, teacher=teacher, default_room=room)

    session = ClassSession.objects.create(course=course, room=room, teacher=teacher, status=ClassSession.Status.CLOSED)

    from apps.attendance.models import CheckIn

    CheckIn.objects.create(
        session=session,
        student=student,
        status="FLAGGED",
        latitude=6.5244,
        longitude=3.3792,
        accuracy_m=10,
        distance_m=30,
        checked_in_at=timezone.now(),
    )

    clock = DefaultClock()

    with pytest.raises(ConflictError, match="Cannot finalize"):
        finalize_session(
            session_id=str(session.id),
            teacher=teacher,
            clock=clock,
        )


@pytest.mark.django_db
def test_generate_qr_token_success():
    """Test generating QR token for an open session."""
    term = Term.objects.create(name="Term 1", starts_on="2024-01-01", ends_on="2024-06-30", is_current=True)
    room = Room.objects.create(name="Room 101", latitude=6.5244, longitude=3.3792, radius_m=50)
    teacher = User.objects.create_user(email="teacher@example.com", full_name="Teacher", role="teacher")
    course = Course.objects.create(code="CS101", title="Intro to CS", term=term, teacher=teacher, default_room=room)

    session = ClassSession.objects.create(course=course, room=room, teacher=teacher, status=ClassSession.Status.OPEN)

    token = generate_qr_token(
        session_id=str(session.id),
        teacher=teacher,
        max_age_seconds=20,
    )

    assert token is not None
    assert isinstance(token, str)


@pytest.mark.django_db
def test_generate_qr_token_not_open_fails():
    """Test generating QR token for a non-open session fails."""
    term = Term.objects.create(name="Term 1", starts_on="2024-01-01", ends_on="2024-06-30", is_current=True)
    room = Room.objects.create(name="Room 101", latitude=6.5244, longitude=3.3792, radius_m=50)
    teacher = User.objects.create_user(email="teacher@example.com", full_name="Teacher", role="teacher")
    course = Course.objects.create(code="CS101", title="Intro to CS", term=term, teacher=teacher, default_room=room)

    session = ClassSession.objects.create(course=course, room=room, teacher=teacher, status=ClassSession.Status.SCHEDULED)

    with pytest.raises(BadRequestError, match="Session is not open"):
        generate_qr_token(
            session_id=str(session.id),
            teacher=teacher,
            max_age_seconds=20,
        )


@pytest.mark.django_db
def test_scheduled_end_automatically_closes_session_and_stops_qr():
    term = Term.objects.create(name="Term 1", starts_on="2024-01-01", ends_on="2024-06-30", is_current=True)
    room = Room.objects.create(name="Room 101", latitude=6.5244, longitude=3.3792, radius_m=50)
    teacher = User.objects.create_user(email="teacher@example.com", full_name="Teacher", role="teacher")
    course = Course.objects.create(code="CS101", title="Intro to CS", term=term, teacher=teacher, default_room=room)
    now = timezone.now()
    session = ClassSession.objects.create(
        course=course,
        room=room,
        teacher=teacher,
        status=ClassSession.Status.OPEN,
        scheduled_start_at=now - timedelta(hours=1),
        scheduled_end_at=now - timedelta(seconds=1),
    )

    with pytest.raises(BadRequestError, match="Session is not open"):
        generate_qr_token(str(session.id), teacher, 15)

    session.refresh_from_db()
    assert session.status == ClassSession.Status.CLOSED
    assert session.closed_at == session.scheduled_end_at


@pytest.mark.django_db
def test_generate_qr_token_not_owner_fails():
    """Test generating QR token by non-owner fails."""
    term = Term.objects.create(name="Term 1", starts_on="2024-01-01", ends_on="2024-06-30", is_current=True)
    room = Room.objects.create(name="Room 101", latitude=6.5244, longitude=3.3792, radius_m=50)
    teacher = User.objects.create_user(email="teacher@example.com", full_name="Teacher", role="teacher")
    other_teacher = User.objects.create_user(email="other@example.com", full_name="Other", role="teacher")
    course = Course.objects.create(code="CS101", title="Intro to CS", term=term, teacher=teacher, default_room=room)

    session = ClassSession.objects.create(course=course, room=room, teacher=teacher, status=ClassSession.Status.OPEN)

    with pytest.raises(NotFoundError):
        generate_qr_token(
            session_id=str(session.id),
            teacher=other_teacher,
            max_age_seconds=20,
        )
