import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.academics.models import Course, Enrollment, Room, Term
from apps.accounts.models import User
from apps.attendance.adapters.qr import DjangoQRTokenAdapter
from apps.attendance.models import ClassSession


@pytest.mark.django_db
def test_begin_checkin_returns_room_radius_for_location_prompt():
    teacher = User.objects.create_user(
        email="teacher@example.com",
        full_name="Teacher",
        role=User.Role.TEACHER,
    )
    student = User.objects.create_user(
        email="student@example.com",
        full_name="Student",
        role=User.Role.STUDENT,
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
    Enrollment.objects.create(course=course, student=student)
    session = ClassSession.objects.create(
        course=course,
        room=room,
        teacher=teacher,
        status=ClassSession.Status.OPEN,
    )
    client = APIClient()
    client.force_authenticate(user=student)

    response = client.post(
        reverse("begin_checkin"),
        {
            "session_id": str(session.id),
            "qr_token": DjangoQRTokenAdapter().generate_token(str(session.id)),
        },
        format="json",
    )

    assert response.status_code == 200
    assert response.data["classroom"] == {"lat": 6.5244, "lng": 3.3792, "radius_m": 50}
