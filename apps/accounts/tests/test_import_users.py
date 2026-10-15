import pytest

from apps.accounts.models import ActivationCode, User
from apps.accounts.services.import_users import import_users_from_csv
from apps.core.clock import DefaultClock


@pytest.mark.django_db
def test_import_users_from_csv():
    admin = User.objects.create_user(
        email="admin@example.com",
        full_name="Admin User",
        role="ADMIN",
        password="adminpass",
    )

    csv_data = """student_number,full_name,email,course_codes
ST001,John Doe,john@example.com,MATH101
ST002,Jane Smith,jane@example.com,CS101"""

    clock = DefaultClock()
    result = import_users_from_csv(csv_data, admin, clock)

    assert result["created"] == 2
    assert result["updated"] == 0
    assert len(result["errors"]) == 0

    assert User.objects.filter(student_number="ST001").exists()
    assert User.objects.filter(student_number="ST002").exists()


@pytest.mark.django_db
def test_import_users_creates_activation_codes():
    admin = User.objects.create_user(
        email="admin@example.com",
        full_name="Admin User",
        role="ADMIN",
        password="adminpass",
    )

    csv_data = (
        "student_number,full_name,email,course_codes\n"
        "ST001,John Doe,john@example.com,MATH101"
    )

    clock = DefaultClock()
    import_users_from_csv(csv_data, admin, clock)

    user = User.objects.get(student_number="ST001")
    assert ActivationCode.objects.filter(user=user).exists()


@pytest.mark.django_db
def test_import_users_updates_existing():
    admin = User.objects.create_user(
        email="admin@example.com",
        full_name="Admin User",
        role="ADMIN",
        password="adminpass",
    )

    User.objects.create_user(
        email="john@example.com",
        full_name="John Doe",
        role="STUDENT",
        student_number="ST001",
        password="testpass",
    )

    csv_data = (
        "student_number,full_name,email,course_codes\n"
        "ST001,John Updated,john@example.com,MATH101"
    )

    clock = DefaultClock()
    result = import_users_from_csv(csv_data, admin, clock)

    assert result["created"] == 0
    assert result["updated"] == 1

    user = User.objects.get(student_number="ST001")
    assert user.full_name == "John Updated"


@pytest.mark.django_db
def test_import_users_handles_invalid_data():
    admin = User.objects.create_user(
        email="admin@example.com",
        full_name="Admin User",
        role="ADMIN",
        password="adminpass",
    )

    csv_data = "student_number,full_name,email,course_codes\n,John Doe,john@example.com,MATH101"

    clock = DefaultClock()
    result = import_users_from_csv(csv_data, admin, clock)

    assert result["created"] == 0
    assert len(result["errors"]) == 1
