import pytest

from apps.attendance.adapters.qr import DjangoQRTokenAdapter, QRTokenError


def test_generate_and_verify_token():
    """Test token generation and verification."""
    adapter = DjangoQRTokenAdapter()
    session_id = "session-123"

    token = adapter.generate_token(session_id)
    assert token is not None
    assert isinstance(token, str)

    verified = adapter.verify_token(token, session_id)
    assert verified is True


def test_verify_token_wrong_session():
    """Test verification fails for wrong session ID."""
    adapter = DjangoQRTokenAdapter()
    session_id = "session-123"
    wrong_session_id = "session-456"

    token = adapter.generate_token(session_id)

    verified = adapter.verify_token(token, wrong_session_id)
    assert verified is False


def test_verify_token_invalid_signature():
    """Test verification fails for tampered token."""
    adapter = DjangoQRTokenAdapter()
    session_id = "session-123"

    token = adapter.generate_token(session_id)
    tampered_token = token + "tampered"

    with pytest.raises(QRTokenError):
        adapter.verify_token(tampered_token, session_id)


def test_verify_token_expired():
    """Test verification fails for expired token."""
    adapter = DjangoQRTokenAdapter(max_age_seconds=1)
    session_id = "session-123"

    token = adapter.generate_token(session_id)

    # Wait for token to expire
    import time

    time.sleep(1.1)

    with pytest.raises(QRTokenError):
        adapter.verify_token(token, session_id)


def test_generate_token_with_custom_max_age():
    """Test token generation with custom max age."""
    adapter = DjangoQRTokenAdapter(max_age_seconds=60)
    session_id = "session-123"

    token = adapter.generate_token(session_id)
    assert token is not None

    # Should verify immediately
    verified = adapter.verify_token(token, session_id)
    assert verified is True
