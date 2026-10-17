import pytest
from django.utils import timezone

from apps.academics.models import Course, Enrollment, Room, Term
from apps.accounts.models import User
from apps.attendance.models import CheckIn, ClassSession


@pytest.mark.django_db
def test_student_sees_current_projection_and_sessions_needed(client):
    teacher = User.objects.create_user(
        email="teacher@example.com",
        full_name="Teacher",
        role=User.Role.TEACHER,
    )
    student = User.objects.create_user(
        email="student@example.com",
        full_name="Student Example",
        role=User.Role.STUDENT,
        student_number="S-104",
        is_active=True,
    )
    term = Term.objects.create(
        name="Current Term",
        starts_on="2026-01-01",
        ends_on="2026-12-31",
        is_current=True,
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
        planned_sessions=20,
    )
    Enrollment.objects.create(course=course, student=student)
    sessions = [
        ClassSession.objects.create(
            course=course,
            room=room,
            teacher=teacher,
            status=ClassSession.Status.CLOSED,
        )
        for _ in range(4)
    ]
    for session in sessions[:3]:
        CheckIn.objects.create(
            session=session,
            student=student,
            status=CheckIn.Status.PRESENT,
            device_hint="student-device",
            checked_in_at=timezone.now(),
        )
    client.force_login(student)

    response = client.get("/student/attendance/")

    assert response.status_code == 200
    assert b"75%" in response.content
    assert b"13 of 16 remaining classes needed for 80%" in response.content
    assert b"Below target, still reachable" in response.content


@pytest.mark.django_db
def test_teacher_cannot_open_student_attendance_forecast(client):
    teacher = User.objects.create_user(
        email="teacher@example.com",
        full_name="Teacher",
        role=User.Role.TEACHER,
        is_active=True,
    )
    client.force_login(teacher)

    response = client.get("/student/attendance/")

    assert response.status_code == 403
