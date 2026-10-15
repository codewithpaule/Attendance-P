import pytest

from apps.accounts.models import User
from apps.audit.services.record import record


@pytest.mark.django_db
def test_record_creates_audit_log():
    user = User.objects.create_user(
        email="test@example.com",
        full_name="Test User",
        role="STUDENT",
        password="testpass123",
    )
    audit = record(
        actor=user,
        action="TEST_ACTION",
        target_type="TestModel",
        target_id="123",
        metadata={"key": "value"},
        ip="127.0.0.1",
    )
    assert audit.actor == user
    assert audit.action == "TEST_ACTION"
    assert audit.target_type == "TestModel"
    assert audit.target_id == "123"
    assert audit.metadata == {"key": "value"}
    assert audit.ip == "127.0.0.1"


@pytest.mark.django_db
def test_record_without_actor():
    audit = record(
        actor=None,
        action="SYSTEM_ACTION",
        target_type="TestModel",
        target_id="456",
    )
    assert audit.actor is None
    assert audit.action == "SYSTEM_ACTION"
