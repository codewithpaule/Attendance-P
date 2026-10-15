import pytest

from apps.accounts.models import User
from apps.accounts.selectors.functions import (
    get_active_passkey,
    get_passkey,
    get_user_by_email,
    get_user_by_student_number,
    list_passkeys,
)


@pytest.mark.django_db
def test_get_user_by_email():
    user = User.objects.create_user(
        email="test@example.com",
        full_name="Test User",
        role="STUDENT",
        password="testpass123",
    )
    found = get_user_by_email("test@example.com")
    assert found == user


@pytest.mark.django_db
def test_get_user_by_email_not_found():
    found = get_user_by_email("nonexistent@example.com")
    assert found is None


@pytest.mark.django_db
def test_get_user_by_student_number():
    user = User.objects.create_user(
        email="test@example.com",
        full_name="Test User",
        role="STUDENT",
        student_number="ST12345",
        password="testpass123",
    )
    found = get_user_by_student_number("ST12345")
    assert found == user


@pytest.mark.django_db
def test_list_passkeys():
    user = User.objects.create_user(
        email="test@example.com",
        full_name="Test User",
        role="STUDENT",
        password="testpass123",
    )
    user.passkey_credentials.create(
        credential_id="cred1", public_key="key1", sign_count=0, label="Device 1"
    )
    passkey2 = user.passkey_credentials.create(
        credential_id="cred2", public_key="key2", sign_count=0, label="Device 2"
    )
    passkey2.revoked_at = None

    passkeys = list_passkeys(user)
    assert len(passkeys) == 2
    assert passkeys[0].credential_id == "cred2"


@pytest.mark.django_db
def test_get_passkey():
    user = User.objects.create_user(
        email="test@example.com",
        full_name="Test User",
        role="STUDENT",
        password="testpass123",
    )
    passkey = user.passkey_credentials.create(
        credential_id="cred1", public_key="key1", sign_count=0, label="Device 1"
    )

    found = get_passkey("cred1", user)
    assert found == passkey


@pytest.mark.django_db
def test_get_active_passkey():
    user = User.objects.create_user(
        email="test@example.com",
        full_name="Test User",
        role="STUDENT",
        password="testpass123",
    )
    passkey = user.passkey_credentials.create(
        credential_id="cred1", public_key="key1", sign_count=0, label="Device 1"
    )

    found = get_active_passkey("cred1")
    assert found == passkey
