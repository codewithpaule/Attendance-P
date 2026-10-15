import pytest

from apps.academics.models import AdvisorAssignment
from apps.academics.services.import_advisors import import_advisor_assignments_from_csv
from apps.accounts.models import User
from apps.core.clock import DefaultClock


@pytest.mark.django_db
def test_import_advisor_assignments_from_csv():
    admin = User.objects.create_user(
        email="admin@example.com",
        full_name="Admin User",
        role="ADMIN",
        password="adminpass",
    )

    advisor = User.objects.create_user(
        email="advisor@example.com",
        full_name="Advisor User",
        role="ADVISOR",
        password="advisorpass",
    )

    student = User.objects.create_user(
        email="student@example.com",
        full_name="Student User",
        role="STUDENT",
        student_number="ST001",
        password="studentpass",
    )

    csv_data = "advisor_email,student_number\nadvisor@example.com,ST001"

    clock = DefaultClock()
    result = import_advisor_assignments_from_csv(csv_data, admin, clock)

    assert result["created"] == 1
    assert result["updated"] == 0
    assert len(result["errors"]) == 0

    assert AdvisorAssignment.objects.filter(advisor=advisor, student=student).exists()


@pytest.mark.django_db
def test_import_advisor_assignments_updates_existing():
    admin = User.objects.create_user(
        email="admin@example.com",
        full_name="Admin User",
        role="ADMIN",
        password="adminpass",
    )

    advisor = User.objects.create_user(
        email="advisor@example.com",
        full_name="Advisor User",
        role="ADVISOR",
        password="advisorpass",
    )

    student = User.objects.create_user(
        email="student@example.com",
        full_name="Student User",
        role="STUDENT",
        student_number="ST001",
        password="studentpass",
    )

    AdvisorAssignment.objects.create(advisor=advisor, student=student)

    csv_data = "advisor_email,student_number\nadvisor@example.com,ST001"

    clock = DefaultClock()
    result = import_advisor_assignments_from_csv(csv_data, admin, clock)

    assert result["created"] == 0
    assert result["updated"] == 1


@pytest.mark.django_db
def test_import_advisor_assignments_invalid_advisor():
    admin = User.objects.create_user(
        email="admin@example.com",
        full_name="Admin User",
        role="ADMIN",
        password="adminpass",
    )

    User.objects.create_user(
        email="student@example.com",
        full_name="Student User",
        role="STUDENT",
        student_number="ST001",
        password="studentpass",
    )

    csv_data = "advisor_email,student_number\nnonexistent@example.com,ST001"

    clock = DefaultClock()
    result = import_advisor_assignments_from_csv(csv_data, admin, clock)

    assert result["created"] == 0
    assert len(result["errors"]) == 1
