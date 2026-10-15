import pytest

from apps.academics.models import Course, Enrollment, Term
from apps.academics.services.import_enrollments import import_enrollments_from_csv
from apps.accounts.models import User
from apps.core.clock import DefaultClock


@pytest.mark.django_db
def test_import_enrollments_from_csv():
    admin = User.objects.create_user(
        email="admin@example.com",
        full_name="Admin User",
        role="ADMIN",
        password="adminpass",
    )

    term = Term.objects.create(name="2024-1", starts_on="2024-01-01", ends_on="2024-05-31")

    teacher = User.objects.create_user(
        email="teacher@example.com",
        full_name="Teacher User",
        role="TEACHER",
        password="teacherpass",
    )

    course = Course.objects.create(
        code="MATH101",
        title="Mathematics 101",
        term=term,
        teacher=teacher,
        planned_sessions=12,
    )

    student = User.objects.create_user(
        email="student@example.com",
        full_name="Student User",
        role="STUDENT",
        student_number="ST001",
        password="studentpass",
    )

    csv_data = "student_number,course_code\nST001,MATH101"

    clock = DefaultClock()
    result = import_enrollments_from_csv(csv_data, admin, clock)

    assert result["created"] == 1
    assert result["updated"] == 0
    assert len(result["errors"]) == 0

    assert Enrollment.objects.filter(student=student, course=course).exists()


@pytest.mark.django_db
def test_import_enrollments_updates_existing():
    admin = User.objects.create_user(
        email="admin@example.com",
        full_name="Admin User",
        role="ADMIN",
        password="adminpass",
    )

    term = Term.objects.create(name="2024-1", starts_on="2024-01-01", ends_on="2024-05-31")

    teacher = User.objects.create_user(
        email="teacher@example.com",
        full_name="Teacher User",
        role="TEACHER",
        password="teacherpass",
    )

    course = Course.objects.create(
        code="MATH101",
        title="Mathematics 101",
        term=term,
        teacher=teacher,
        planned_sessions=12,
    )

    student = User.objects.create_user(
        email="student@example.com",
        full_name="Student User",
        role="STUDENT",
        student_number="ST001",
        password="studentpass",
    )

    Enrollment.objects.create(student=student, course=course)

    csv_data = "student_number,course_code\nST001,MATH101"

    clock = DefaultClock()
    result = import_enrollments_from_csv(csv_data, admin, clock)

    assert result["created"] == 0
    assert result["updated"] == 1


@pytest.mark.django_db
def test_import_enrollments_invalid_student():
    admin = User.objects.create_user(
        email="admin@example.com",
        full_name="Admin User",
        role="ADMIN",
        password="adminpass",
    )

    term = Term.objects.create(name="2024-1", starts_on="2024-01-01", ends_on="2024-05-31")

    teacher = User.objects.create_user(
        email="teacher@example.com",
        full_name="Teacher User",
        role="TEACHER",
        password="teacherpass",
    )

    Course.objects.create(
        code="MATH101",
        title="Mathematics 101",
        term=term,
        teacher=teacher,
        planned_sessions=12,
    )

    csv_data = "student_number,course_code\nST999,MATH101"

    clock = DefaultClock()
    result = import_enrollments_from_csv(csv_data, admin, clock)

    assert result["created"] == 0
    assert len(result["errors"]) == 1
