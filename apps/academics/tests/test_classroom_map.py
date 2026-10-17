import pytest
from django.urls import reverse

from apps.academics.models import Course, Room, Term
from apps.accounts.models import User
from apps.attendance.models import ClassSession
from apps.audit.models import AuditLog


@pytest.fixture
def teacher(db):
    return User.objects.create_user(
        email="teacher@example.com",
        password="test-password",
        full_name="Test Teacher",
        role=User.Role.TEACHER,
        is_active=True,
    )


@pytest.fixture
def course(teacher):
    term = Term.objects.create(
        name="Test Term",
        starts_on="2026-01-01",
        ends_on="2026-06-01",
    )
    return Course.objects.create(
        code="CS101",
        title="Computer Science",
        term=term,
        teacher=teacher,
    )


@pytest.mark.django_db
def test_teacher_can_set_course_classroom_location(client, teacher, course):
    client.force_login(teacher)

    response = client.post(
        reverse("classroom_map"),
        {
            "course_id": str(course.id),
            "room_name": "Engineering Hall",
            "latitude": "6.5244000",
            "longitude": "3.3792000",
            "radius_m": "150",
        },
    )

    assert response.status_code == 302
    room = Room.objects.get(name="Engineering Hall")
    course.refresh_from_db()
    assert course.default_room == room
    assert float(room.latitude) == pytest.approx(6.5244)
    assert float(room.longitude) == pytest.approx(3.3792)
    assert room.radius_m == 150
    assert AuditLog.objects.filter(action="CLASSROOM_LOCATION_UPDATED").exists()


@pytest.mark.django_db
def test_teacher_cannot_edit_another_teachers_course(client, teacher, course):
    other_teacher = User.objects.create_user(
        email="other@example.com",
        password="test-password",
        full_name="Other Teacher",
        role=User.Role.TEACHER,
        is_active=True,
    )
    client.force_login(other_teacher)

    response = client.post(
        reverse("classroom_map"),
        {
            "course_id": str(course.id),
            "room_name": "Unauthorized Room",
            "latitude": "6.5",
            "longitude": "3.3",
            "radius_m": "100",
        },
    )

    assert response.status_code == 403
    assert not Room.objects.filter(name="Unauthorized Room").exists()
    assert not AuditLog.objects.filter(action="CLASSROOM_LOCATION_UPDATED").exists()


@pytest.mark.django_db
def test_updating_shared_room_keeps_other_course_location_unchanged(client, teacher, course):
    other_teacher = User.objects.create_user(
        email="colleague@example.com",
        password="test-password",
        full_name="Colleague",
        role=User.Role.TEACHER,
        is_active=True,
    )
    room = Room.objects.create(
        name="Shared Hall",
        latitude="6.5000000",
        longitude="3.3000000",
        radius_m=100,
    )
    course.default_room = room
    course.save()
    other_course = Course.objects.create(
        code="CS102",
        title="Algorithms",
        term=course.term,
        teacher=other_teacher,
        default_room=room,
    )
    client.force_login(teacher)

    response = client.post(
        reverse("classroom_map"),
        {
            "course_id": str(course.id),
            "room_name": "Engineering Hall",
            "latitude": "6.5244000",
            "longitude": "3.3792000",
            "radius_m": "150",
        },
    )

    assert response.status_code == 302
    course.refresh_from_db()
    other_course.refresh_from_db()
    room.refresh_from_db()
    assert course.default_room_id != room.id
    assert other_course.default_room == room
    assert float(room.latitude) == pytest.approx(6.5)
    assert room.radius_m == 100


@pytest.mark.django_db
def test_shared_room_requires_a_distinct_name_to_fork(client, teacher, course):
    other_teacher = User.objects.create_user(
        email="another-colleague@example.com",
        password="test-password",
        full_name="Another Colleague",
        role=User.Role.TEACHER,
        is_active=True,
    )
    room = Room.objects.create(
        name="Shared Hall",
        latitude="6.5000000",
        longitude="3.3000000",
        radius_m=100,
    )
    course.default_room = room
    course.save()
    Course.objects.create(
        code="CS103",
        title="Databases",
        term=course.term,
        teacher=other_teacher,
        default_room=room,
    )
    client.force_login(teacher)

    response = client.post(
        reverse("classroom_map"),
        {
            "course_id": str(course.id),
            "room_name": "Shared Hall",
            "latitude": "6.5244000",
            "longitude": "3.3792000",
            "radius_m": "150",
        },
    )

    assert response.status_code == 200
    assert "Choose a distinct name" in response.content.decode()
    assert Room.objects.count() == 1
    room.refresh_from_db()
    assert float(room.latitude) == pytest.approx(6.5)
    assert room.radius_m == 100


@pytest.mark.django_db
def test_teacher_classroom_map_shows_qr_link_for_active_session(client, teacher, course):
    room = Room.objects.create(
        name="Engineering Hall",
        latitude="6.5244000",
        longitude="3.3792000",
        radius_m=50,
    )
    course.default_room = room
    course.save()
    session = ClassSession.objects.create(
        course=course,
        room=room,
        teacher=teacher,
        status=ClassSession.Status.OPEN,
    )
    client.force_login(teacher)

    response = client.get(reverse("classroom_map"))

    assert response.status_code == 200
    assert f"/teacher/qr/{session.id}/" in response.content.decode()


@pytest.mark.django_db
def test_non_teacher_cannot_open_classroom_map(client):
    student = User.objects.create_user(
        email="student@example.com",
        password="test-password",
        full_name="Test Student",
        role=User.Role.STUDENT,
        is_active=True,
    )
    client.force_login(student)

    response = client.get(reverse("classroom_map"))

    assert response.status_code == 403


@pytest.mark.django_db
def test_classroom_map_requires_login(client):
    response = client.get(reverse("classroom_map"))

    assert response.status_code == 302
    assert "/login/" in response.url
