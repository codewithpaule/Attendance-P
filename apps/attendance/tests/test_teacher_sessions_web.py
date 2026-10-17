import base64
from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.academics.models import Course, Room, Term
from apps.accounts.models import User
from apps.attendance.models import ClassSession


@pytest.mark.django_db
def test_teacher_can_schedule_session_with_start_and_end(client):
    teacher = User.objects.create_user(
        email="teacher@example.com",
        full_name="Teacher",
        role=User.Role.TEACHER,
        is_active=True,
    )
    term = Term.objects.create(
        name="Term 1",
        starts_on="2024-01-01",
        ends_on="2024-06-30",
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
    )
    client.force_login(teacher)
    start_at = timezone.localtime(timezone.now() + timedelta(hours=1)).replace(second=0, microsecond=0)
    end_at = start_at + timedelta(minutes=90)

    response = client.post(
        "/teacher/sessions/",
        {
            "action": "schedule",
            "course": str(course.id),
            "scheduled_start_at": start_at.strftime("%Y-%m-%dT%H:%M"),
            "scheduled_end_at": end_at.strftime("%Y-%m-%dT%H:%M"),
        },
        follow=True,
    )

    session = ClassSession.objects.get(course=course)
    assert response.status_code == 200
    assert session.room == room
    assert timezone.localtime(session.scheduled_start_at) == start_at
    assert timezone.localtime(session.scheduled_end_at) == end_at
    assert b"Start check-in" in response.content


@pytest.mark.django_db
def test_student_cannot_access_teacher_session_page(client):
    student = User.objects.create_user(
        email="student@example.com",
        full_name="Student",
        role=User.Role.STUDENT,
        is_active=True,
    )
    client.force_login(student)

    response = client.get("/teacher/sessions/")

    assert response.status_code == 403


@pytest.mark.django_db
def test_student_checkin_page_renders_camera_scanner_controls(client):
    student = User.objects.create_user(
        email="student@example.com",
        full_name="Student",
        role=User.Role.STUDENT,
        is_active=True,
    )
    client.force_login(student)

    response = client.get("/checkin/")

    assert response.status_code == 200
    assert b'id="camera-start-btn"' in response.content
    assert b'id="qr-camera"' in response.content
    assert b'id="camera-status"' in response.content


@pytest.mark.django_db
def test_teacher_qr_api_returns_renderable_svg(client):
    teacher = User.objects.create_user(
        email="teacher@example.com",
        full_name="Teacher",
        role=User.Role.TEACHER,
        is_active=True,
    )
    term = Term.objects.create(
        name="Term 1",
        starts_on="2024-01-01",
        ends_on="2024-06-30",
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
    )
    session = ClassSession.objects.create(
        course=course,
        room=room,
        teacher=teacher,
        status=ClassSession.Status.OPEN,
    )
    client.force_login(teacher)

    response = client.get(reverse("qr_token", kwargs={"session_id": session.id}))

    assert response.status_code == 200
    assert response.data["token"]
    assert response.data["qr_svg"].startswith("data:image/svg+xml;base64,")
    svg_bytes = base64.b64decode(response.data["qr_svg"].split(",", 1)[1])
    assert b"<svg" in svg_bytes


@pytest.mark.django_db
def test_teacher_qr_page_has_image_target_and_live_status(client):
    teacher = User.objects.create_user(
        email="teacher@example.com",
        full_name="Teacher",
        role=User.Role.TEACHER,
        is_active=True,
    )
    term = Term.objects.create(
        name="Term 1",
        starts_on="2024-01-01",
        ends_on="2024-06-30",
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
    )
    session = ClassSession.objects.create(
        course=course,
        room=room,
        teacher=teacher,
        status=ClassSession.Status.OPEN,
    )
    client.force_login(teacher)

    response = client.get(reverse("teacher_qr", kwargs={"session_id": session.id}))

    assert response.status_code == 200
    assert b'id="qr-code-image"' in response.content
    assert b'id="qr-status"' in response.content
    assert b"qrcode.min.js" not in response.content
