import pytest
from django.urls import reverse

from apps.accounts.admin import AccountAdminForm
from apps.accounts.models import ActivationCode, User


@pytest.mark.django_db
def test_teacher_admin_form_does_not_require_student_number():
    form = AccountAdminForm(
        data={
            "email": "teacher@example.com",
            "full_name": "Teacher Example",
            "role": User.Role.TEACHER,
            "student_number": "",
        }
    )

    assert form.is_valid(), form.errors


@pytest.mark.django_db
def test_student_admin_form_requires_student_number():
    form = AccountAdminForm(
        data={
            "email": "student@example.com",
            "full_name": "Student Example",
            "role": User.Role.STUDENT,
            "student_number": "",
        }
    )

    assert not form.is_valid()
    assert "student_number" in form.errors


def test_admin_form_does_not_offer_admin_role():
    form = AccountAdminForm()

    assert User.Role.ADMIN not in dict(form.fields["role"].choices)


@pytest.mark.django_db
def test_admin_can_create_teacher_without_student_number(client):
    admin_user = User.objects.create_superuser(
        email="admin@example.com",
        password="StrongAdminPass!234",
        full_name="Admin Example",
        role=User.Role.ADMIN,
        is_active=True,
    )
    client.force_login(admin_user)

    response = client.post(
        reverse("admin:accounts_user_add"),
        {
            "email": "teacher@example.com",
            "full_name": "Teacher Example",
            "role": User.Role.TEACHER,
            "student_number": "",
            "_save": "Save",
        },
        follow=True,
    )

    teacher = User.objects.get(email="teacher@example.com")
    activation = ActivationCode.objects.get(user=teacher)
    assert response.status_code == 200
    assert teacher.student_number is None
    assert not teacher.is_active
    assert not teacher.has_usable_password()
    assert activation.purpose == ActivationCode.Purpose.ACTIVATION
    assert "One-time activation code" in response.content.decode()


@pytest.mark.django_db
def test_admin_can_create_student_with_student_number(client):
    admin_user = User.objects.create_superuser(
        email="admin@example.com",
        password="StrongAdminPass!234",
        full_name="Admin Example",
        role=User.Role.ADMIN,
        is_active=True,
    )
    client.force_login(admin_user)

    response = client.post(
        reverse("admin:accounts_user_add"),
        {
            "email": "student@example.com",
            "full_name": "Student Example",
            "role": User.Role.STUDENT,
            "student_number": "ST-1001",
            "_save": "Save",
        },
        follow=True,
    )

    assert response.status_code == 200
    assert User.objects.filter(email="student@example.com", student_number="ST-1001").exists()
    assert ActivationCode.objects.filter(
        user__email="student@example.com",
        purpose=ActivationCode.Purpose.ACTIVATION,
    ).exists()
