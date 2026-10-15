import pytest

from apps.accounts.models import ActivationCode, User
from apps.accounts.selectors.functions import get_user_by_student_number
from apps.accounts.services.recovery import (
    issue_recovery_code as issue_recovery_code_service,
)
from apps.accounts.services.recovery import (
    use_recovery_code as use_recovery_code_service,
)
from apps.core.clock import DefaultClock


@pytest.mark.django_db
def test_issue_recovery_code():
    advisor = User.objects.create_user(
        email="advisor@example.com",
        full_name="Advisor User",
        role="ADVISOR",
        password="advisorpass",
    )

    User.objects.create_user(
        email="student@example.com",
        full_name="Student User",
        role="STUDENT",
        student_number="ST001",
        password="studentpass",
    )

    clock = DefaultClock()
    code = issue_recovery_code_service("ST001", advisor, clock)

    assert len(code) == 8
    assert ActivationCode.objects.filter(
        user__student_number="ST001", purpose=ActivationCode.Purpose.RECOVERY
    ).exists()


@pytest.mark.django_db
def test_issue_recovery_code_requires_admin_or_advisor_raises_permission_denied():
    User.objects.create_user(
        email="student@example.com",
        full_name="Student User",
        role="STUDENT",
        student_number="ST001",
        password="studentpass",
    )

    another_student = User.objects.create_user(
        email="another@example.com",
        full_name="Another User",
        role="STUDENT",
        student_number="ST002",
        password="studentpass",
    )

    clock = DefaultClock()

    from apps.core.exceptions import PermissionDeniedError

    try:
        issue_recovery_code_service("ST001", another_student, clock)
        raise AssertionError("Should have raised PermissionDeniedError")
    except PermissionDeniedError:
        pass  # Expected


@pytest.mark.django_db
def test_use_recovery_code():
    User.objects.create_user(
        email="student@example.com",
        full_name="Student User",
        role="STUDENT",
        student_number="ST001",
        password="oldpass",
    )

    advisor = User.objects.create_user(
        email="advisor@example.com",
        full_name="Advisor User",
        role="ADVISOR",
        password="advisorpass",
    )

    clock = DefaultClock()
    code = issue_recovery_code_service("ST001", advisor, clock)

    user = get_user_by_student_number("ST001")
    assert user.check_password("oldpass")

    user = use_recovery_code_service("ST001", code, "newpass123", clock)

    assert user.check_password("newpass123")
    assert not user.check_password("oldpass")


@pytest.mark.django_db
def test_use_recovery_code_marks_as_used():
    student = User.objects.create_user(
        email="student@example.com",
        full_name="Student User",
        role="STUDENT",
        student_number="ST001",
        password="oldpass",
    )

    advisor = User.objects.create_user(
        email="advisor@example.com",
        full_name="Advisor User",
        role="ADVISOR",
        password="advisorpass",
    )

    clock = DefaultClock()
    code = issue_recovery_code_service("ST001", advisor, clock)

    use_recovery_code_service("ST001", code, "newpass123", clock)

    recovery_code = ActivationCode.objects.filter(
        user=student, purpose=ActivationCode.Purpose.RECOVERY
    ).first()
    assert recovery_code.used_at is not None
