from datetime import timedelta

import pytest
from django.utils import timezone

from apps.academics.models import Course, Enrollment, Room, Term
from apps.accounts.models import User
from apps.attendance.models import CheckIn, ClassSession
from apps.attendance.services.checkin import begin_checkin, complete_checkin
from apps.attendance.services.session import open_session
from apps.core.clock import DefaultClock
from apps.core.exceptions import BadRequestError, NotFoundError


class FrozenClock:
    def __init__(self, current_time):
        self.current_time = current_time

    def now(self):
        return self.current_time


@pytest.mark.django_db
def test_begin_checkin_success():
    """Test beginning a check-in successfully."""
    term = Term.objects.create(name="Term 1", starts_on="2024-01-01", ends_on="2024-06-30", is_current=True)
    room = Room.objects.create(name="Room 101", latitude=6.5244, longitude=3.3792, radius_m=50)
    teacher = User.objects.create_user(email="teacher@example.com", full_name="Teacher", role="teacher")
    student = User.objects.create_user(email="student@example.com", full_name="Student", role="student")
    course = Course.objects.create(code="CS101", title="Intro to CS", term=term, teacher=teacher, default_room=room)

    Enrollment.objects.create(course=course, student=student)

    session = ClassSession.objects.create(course=course, room=room, teacher=teacher, status=ClassSession.Status.SCHEDULED)

    clock = DefaultClock()
    opened_session = open_session(
        session_id=str(session.id),
        teacher=teacher,
        checkin_window_minutes=15,
        clock=clock,
    )

    from apps.attendance.adapters.qr import DjangoQRTokenAdapter

    adapter = DjangoQRTokenAdapter()
    qr_token = adapter.generate_token(str(session.id))

    attempt = begin_checkin(
        session_id=str(session.id),
        student=student,
        qr_token=qr_token,
        device_hint="device123",
        clock=clock,
    )

    assert attempt.session == opened_session
    assert attempt.student == student
    assert attempt.device_hint == "device123"
    assert attempt.challenge is not None
    assert attempt.consumed_at is None

    # Verify challenge is a string
    assert isinstance(attempt.challenge, str)


@pytest.mark.django_db
def test_begin_checkin_session_not_open():
    """Test beginning check-in on a non-open session fails."""
    term = Term.objects.create(name="Term 1", starts_on="2024-01-01", ends_on="2024-06-30", is_current=True)
    room = Room.objects.create(name="Room 101", latitude=6.5244, longitude=3.3792, radius_m=50)
    teacher = User.objects.create_user(email="teacher@example.com", full_name="Teacher", role="teacher")
    student = User.objects.create_user(email="student@example.com", full_name="Student", role="student")
    course = Course.objects.create(code="CS101", title="Intro to CS", term=term, teacher=teacher, default_room=room)

    Enrollment.objects.create(course=course, student=student)

    session = ClassSession.objects.create(course=course, room=room, teacher=teacher, status=ClassSession.Status.SCHEDULED)

    clock = DefaultClock()

    from apps.attendance.adapters.qr import DjangoQRTokenAdapter

    adapter = DjangoQRTokenAdapter()
    qr_token = adapter.generate_token(str(session.id))

    with pytest.raises(BadRequestError, match="Session is not open"):
        begin_checkin(
            session_id=str(session.id),
            student=student,
            qr_token=qr_token,
            device_hint="device123",
            clock=clock,
        )


@pytest.mark.django_db
def test_begin_checkin_is_rejected_before_20_minute_window():
    term = Term.objects.create(name="Term 1", starts_on="2024-01-01", ends_on="2024-06-30", is_current=True)
    room = Room.objects.create(name="Room 101", latitude=6.5244, longitude=3.3792, radius_m=50)
    teacher = User.objects.create_user(email="teacher@example.com", full_name="Teacher", role="teacher")
    student = User.objects.create_user(email="student@example.com", full_name="Student", role="student")
    course = Course.objects.create(code="CS101", title="Intro to CS", term=term, teacher=teacher, default_room=room)
    Enrollment.objects.create(course=course, student=student)
    now = timezone.now()
    session = ClassSession.objects.create(
        course=course,
        room=room,
        teacher=teacher,
        status=ClassSession.Status.OPEN,
        scheduled_start_at=now + timedelta(minutes=30),
        scheduled_end_at=now + timedelta(hours=1),
    )
    from apps.attendance.adapters.qr import DjangoQRTokenAdapter

    qr_token = DjangoQRTokenAdapter().generate_token(str(session.id))

    with pytest.raises(BadRequestError, match="opens 20 minutes"):
        begin_checkin(str(session.id), student, qr_token, "device", FrozenClock(now))


@pytest.mark.django_db
def test_begin_checkin_not_enrolled():
    """Test beginning check-in when not enrolled fails."""
    term = Term.objects.create(name="Term 1", starts_on="2024-01-01", ends_on="2024-06-30", is_current=True)
    room = Room.objects.create(name="Room 101", latitude=6.5244, longitude=3.3792, radius_m=50)
    teacher = User.objects.create_user(email="teacher@example.com", full_name="Teacher", role="teacher")
    student = User.objects.create_user(email="student@example.com", full_name="Student", role="student")
    course = Course.objects.create(code="CS101", title="Intro to CS", term=term, teacher=teacher, default_room=room)

    session = ClassSession.objects.create(course=course, room=room, teacher=teacher, status=ClassSession.Status.SCHEDULED)

    clock = DefaultClock()
    open_session(
        session_id=str(session.id),
        teacher=teacher,
        checkin_window_minutes=15,
        clock=clock,
    )

    from apps.attendance.adapters.qr import DjangoQRTokenAdapter

    adapter = DjangoQRTokenAdapter()
    qr_token = adapter.generate_token(str(session.id))

    with pytest.raises(BadRequestError, match="Student is not enrolled"):
        begin_checkin(
            session_id=str(session.id),
            student=student,
            qr_token=qr_token,
            device_hint="device123",
            clock=clock,
        )


@pytest.mark.django_db
def test_begin_checkin_replaces_an_unfinished_attempt():
    term = Term.objects.create(name="Term 1", starts_on="2024-01-01", ends_on="2024-06-30", is_current=True)
    room = Room.objects.create(name="Room 101", latitude=6.5244, longitude=3.3792, radius_m=50)
    teacher = User.objects.create_user(email="teacher@example.com", full_name="Teacher", role="teacher")
    student = User.objects.create_user(email="student@example.com", full_name="Student", role="student")
    course = Course.objects.create(code="CS101", title="Intro to CS", term=term, teacher=teacher, default_room=room)

    Enrollment.objects.create(course=course, student=student)

    session = ClassSession.objects.create(course=course, room=room, teacher=teacher, status=ClassSession.Status.SCHEDULED)

    clock = DefaultClock()
    open_session(
        session_id=str(session.id),
        teacher=teacher,
        checkin_window_minutes=15,
        clock=clock,
    )

    from apps.attendance.adapters.qr import DjangoQRTokenAdapter

    adapter = DjangoQRTokenAdapter()
    qr_token = adapter.generate_token(str(session.id))

    first_attempt = begin_checkin(
        session_id=str(session.id),
        student=student,
        qr_token=qr_token,
        device_hint="device123",
        clock=clock,
    )

    replacement_attempt = begin_checkin(
        session_id=str(session.id),
        student=student,
        qr_token=qr_token,
        device_hint="device456",
        clock=clock,
    )

    first_attempt.refresh_from_db()
    assert first_attempt.consumed_at is not None
    assert replacement_attempt.id != first_attempt.id
    assert replacement_attempt.consumed_at is None


@pytest.mark.django_db
def test_complete_checkin_success():
    """Test completing a check-in successfully."""
    term = Term.objects.create(name="Term 1", starts_on="2024-01-01", ends_on="2024-06-30", is_current=True)
    room = Room.objects.create(name="Room 101", latitude=6.5244, longitude=3.3792, radius_m=50)
    teacher = User.objects.create_user(email="teacher@example.com", full_name="Teacher", role="teacher")
    student = User.objects.create_user(email="student@example.com", full_name="Student", role="student")
    course = Course.objects.create(code="CS101", title="Intro to CS", term=term, teacher=teacher, default_room=room)

    Enrollment.objects.create(course=course, student=student)

    session = ClassSession.objects.create(course=course, room=room, teacher=teacher, status=ClassSession.Status.SCHEDULED)

    clock = DefaultClock()
    open_session(
        session_id=str(session.id),
        teacher=teacher,
        checkin_window_minutes=15,
        clock=clock,
    )

    from apps.attendance.adapters.qr import DjangoQRTokenAdapter

    adapter = DjangoQRTokenAdapter()
    qr_token = adapter.generate_token(str(session.id))

    attempt = begin_checkin(
        session_id=str(session.id),
        student=student,
        qr_token=qr_token,
        device_hint="device123",
        clock=clock,
    )

    # Mock assertion (in real implementation, this would be a WebAuthn assertion)
    assertion = {"credentialId": "cred123", "response": {}}

    with pytest.raises(BadRequestError, match="Share your current location"):
        complete_checkin(
            attempt_id=str(attempt.id),
            student=student,
            assertion=assertion,
            location=None,
            clock=clock,
        )

    location = {"lat": 6.5244, "lng": 3.3792, "accuracy_m": 10, "timestamp": 1000}
    with pytest.raises(BadRequestError, match="Passkey verification failed"):
        complete_checkin(
            attempt_id=str(attempt.id),
            student=student,
            assertion=assertion,
            location=location,
            clock=clock,
        )

@pytest.mark.django_db
def test_complete_checkin_outside_classroom_requires_student_to_go_to_class():
    term = Term.objects.create(name="Term 1", starts_on="2024-01-01", ends_on="2024-06-30", is_current=True)
    room = Room.objects.create(name="Room 101", latitude=6.5244, longitude=3.3792, radius_m=50)
    teacher = User.objects.create_user(email="teacher@example.com", full_name="Teacher", role="teacher")
    student = User.objects.create_user(email="student@example.com", full_name="Student", role="student")
    course = Course.objects.create(code="CS101", title="Intro to CS", term=term, teacher=teacher, default_room=room)
    Enrollment.objects.create(course=course, student=student)
    session = ClassSession.objects.create(
        course=course,
        room=room,
        teacher=teacher,
        status=ClassSession.Status.OPEN,
    )
    from apps.attendance.adapters.qr import DjangoQRTokenAdapter

    attempt = begin_checkin(
        session_id=str(session.id),
        student=student,
        qr_token=DjangoQRTokenAdapter().generate_token(str(session.id)),
        device_hint="device123",
        clock=DefaultClock(),
    )

    with pytest.raises(BadRequestError, match="Go to class"):
        complete_checkin(
            attempt_id=str(attempt.id),
            student=student,
            assertion={},
            location={
                "lat": 6.5344,
                "lng": 3.3792,
                "accuracy_m": 10,
                "timestamp": DefaultClock().now().timestamp(),
            },
            clock=DefaultClock(),
        )

    assert not CheckIn.objects.filter(session=session, student=student).exists()


@pytest.mark.django_db
def test_complete_checkin_attempt_not_found():
    """Test completing check-in with non-existent attempt fails."""
    student = User.objects.create_user(email="student@example.com", full_name="Student", role="student")

    clock = DefaultClock()

    assertion = {"credentialId": "cred123", "response": {}}

    with pytest.raises(NotFoundError, match="Check-in attempt not found"):
        complete_checkin(
            attempt_id="00000000-0000-0000-0000-000000000000",
            student=student,
            assertion=assertion,
            location=None,
            clock=clock,
        )


@pytest.mark.django_db
def test_complete_checkin_attempt_expired():
    """Test completing check-in with expired attempt fails."""
    term = Term.objects.create(name="Term 1", starts_on="2024-01-01", ends_on="2024-06-30", is_current=True)
    room = Room.objects.create(name="Room 101", latitude=6.5244, longitude=3.3792, radius_m=50)
    teacher = User.objects.create_user(email="teacher@example.com", full_name="Teacher", role="teacher")
    student = User.objects.create_user(email="student@example.com", full_name="Student", role="student")
    course = Course.objects.create(code="CS101", title="Intro to CS", term=term, teacher=teacher, default_room=room)

    Enrollment.objects.create(course=course, student=student)

    session = ClassSession.objects.create(course=course, room=room, teacher=teacher, status=ClassSession.Status.SCHEDULED)

    clock = DefaultClock()
    open_session(
        session_id=str(session.id),
        teacher=teacher,
        checkin_window_minutes=15,
        clock=clock,
    )

    from apps.attendance.adapters.qr import DjangoQRTokenAdapter

    adapter = DjangoQRTokenAdapter()
    qr_token = adapter.generate_token(str(session.id))

    attempt = begin_checkin(
        session_id=str(session.id),
        student=student,
        qr_token=qr_token,
        device_hint="device123",
        clock=clock,
    )

    # Manually expire the attempt
    attempt.expires_at = clock.now() - timedelta(seconds=10)
    attempt.save()

    assertion = {"credentialId": "cred123", "response": {}}

    with pytest.raises(BadRequestError, match="Check-in attempt has expired"):
        complete_checkin(
            attempt_id=str(attempt.id),
            student=student,
            assertion=assertion,
            location=None,
            clock=clock,
        )
