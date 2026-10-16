import json

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.accounts.models import PasskeyCredential, User


@pytest.mark.django_db
def test_login_page_uses_email_and_has_no_credential_or_student_id_fields(client):
    response = client.get(reverse("login"))
    content = response.content.decode()

    assert response.status_code == 200
    assert 'type="email"' in content
    assert "Passkey Credential" not in content
    assert "Student Number" not in content


@pytest.mark.django_db
def test_activation_page_uses_email_instead_of_student_number(client):
    response = client.get(reverse("activate"))
    content = response.content.decode()

    assert response.status_code == 200
    assert 'type="email"' in content
    assert "student-number" not in content


@pytest.mark.django_db
def test_anonymous_home_redirects_to_project_login(client):
    response = client.get(reverse("home"))

    assert response.status_code == 302
    assert response.url == reverse("login")


@pytest.mark.django_db
def test_teacher_home_redirects_to_classroom_map(client):
    teacher = User.objects.create_user(
        email="teacher@example.com",
        password="test-password",
        full_name="Teacher Example",
        role=User.Role.TEACHER,
        is_active=True,
    )
    client.force_login(teacher)

    response = client.get(reverse("home"))

    assert response.status_code == 302
    assert response.url == reverse("classroom_map")


@pytest.mark.django_db
def test_student_home_redirects_to_checkin(client):
    student = User.objects.create_user(
        email="student@example.com",
        password="test-password",
        full_name="Student Example",
        role=User.Role.STUDENT,
        student_number="ST-1001",
        is_active=True,
    )
    client.force_login(student)

    response = client.get(reverse("home"))

    assert response.status_code == 302
    assert response.url == reverse("student_checkin")


@pytest.mark.django_db
def test_protected_pages_redirect_to_project_login(client):
    checkin_response = client.get(reverse("student_checkin"))
    passkeys_response = client.get(reverse("passkey_management"))
    qr_response = client.get(reverse("teacher_qr", args=["f4f1cc20-cac2-4db1-bab1-67b817a5fc27"]))

    assert checkin_response.status_code == 302
    assert passkeys_response.status_code == 302
    assert qr_response.status_code == 302
    assert checkin_response.url.startswith(reverse("login"))
    assert passkeys_response.url.startswith(reverse("login"))
    assert qr_response.url.startswith(reverse("login"))


@pytest.mark.django_db
def test_login_begin_returns_active_credentials_and_stores_challenge():
    teacher = User.objects.create_user(
        email="teacher@example.com",
        password="test-password",
        full_name="Teacher Example",
        role=User.Role.TEACHER,
        is_active=True,
    )
    PasskeyCredential.objects.create(
        user=teacher,
        credential_id="ZmFrZS1jcmVkZW50aWFs",
        public_key="public-key",
        sign_count=0,
        label="Phone",
    )
    client = APIClient()

    response = client.post(
        reverse("login_begin"),
        {"email": "TEACHER@example.com"},
        format="json",
    )

    assert response.status_code == 200
    assert response.data["allow_credentials"] == ["ZmFrZS1jcmVkZW50aWFs"]
    assert response.data["challenge"]
    assert client.session["webauthn_login_challenge"] == response.data["challenge"]


@pytest.mark.django_db
def test_login_requires_a_server_issued_challenge():
    client = APIClient()

    response = client.post(
        "/api/v1/auth/login",
        {
            "credential_id": "ZmFrZS1jcmVkZW50aWFs",
            "client_data_json": "e30=",
            "authenticator_data": "AA==",
            "signature": "AA==",
        },
        format="json",
    )

    assert response.status_code == 400


@pytest.mark.django_db
def test_activation_options_accept_teacher_email_without_student_number():
    teacher = User.objects.create_user(
        email="teacher@example.com",
        password=None,
        full_name="Teacher Example",
        role=User.Role.TEACHER,
        is_active=False,
    )
    client = APIClient()

    response = client.post(
        reverse("register_passkey_begin_for_activation"),
        {"email": teacher.email},
        format="json",
    )

    assert response.status_code == 200
    assert response.data["user_name"] == teacher.email
    assert client.session["webauthn_activation_challenge"] == response.data["challenge"]


@pytest.mark.django_db
def test_activation_options_work_with_existing_authenticated_session():
    admin = User.objects.create_superuser(
        email="admin@example.com",
        password="StrongAdminPass!234",
        full_name="Admin Example",
        role=User.Role.ADMIN,
        is_active=True,
    )
    teacher = User.objects.create_user(
        email="teacher@example.com",
        password=None,
        full_name="Teacher Example",
        role=User.Role.TEACHER,
        is_active=False,
    )
    client = APIClient(enforce_csrf_checks=True)
    client.force_login(admin)

    response = client.post(
        reverse("register_passkey_begin_for_activation"),
        {"email": teacher.email},
        format="json",
    )

    assert response.status_code == 200
    assert response.data["user_name"] == teacher.email


@pytest.mark.django_db
def test_activation_options_still_accept_legacy_student_number():
    student = User.objects.create_user(
        email="student@example.com",
        password=None,
        full_name="Student Example",
        role=User.Role.STUDENT,
        student_number="ST-1001",
        is_active=False,
    )
    client = APIClient()

    response = client.post(
        reverse("register_passkey_begin_for_activation"),
        {"student_number": student.student_number},
        format="json",
    )

    assert response.status_code == 200
    assert response.data["user_name"] == student.email


@pytest.mark.django_db
def test_activation_options_return_clear_not_found_for_unknown_email():
    client = APIClient()

    response = client.post(
        reverse("register_passkey_begin_for_activation"),
        {"email": "missing@example.invalid"},
        format="json",
    )

    assert response.status_code == 400
    assert json.loads(response.content)["error"]["message"] == "User not found"


@pytest.mark.django_db
def test_activate_already_active_account_returns_handled_conflict():
    teacher = User.objects.create_user(
        email="teacher@example.com",
        password="test-password",
        full_name="Teacher Example",
        role=User.Role.TEACHER,
        is_active=True,
    )
    client = APIClient()
    options = client.post(
        reverse("register_passkey_begin_for_activation"),
        {"email": teacher.email},
        format="json",
    )
    assert options.status_code == 200

    response = client.post(
        "/api/v1/auth/activate",
        {
            "email": teacher.email,
            "code": "ABCD1234",
            "password": "StrongPass!234",
            "credential_id": "ZmFrZS1jcmVkZW50aWFs",
            "client_data_json": "e30=",
            "attestation_object": "AA==",
        },
        format="json",
    )

    assert response.status_code == 400
    assert json.loads(response.content)["error"]["message"] == "User already activated"
