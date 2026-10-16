from unittest.mock import patch

import pytest
from django.test import override_settings

from apps.accounts.adapters.email import send_activation_email


@override_settings(
    RESEND_API_KEY="re_test_key",
    RESEND_FROM_EMAIL="POMSOM <noreply@example.com>",
)
@patch("apps.accounts.adapters.email.resend.Emails.send")
def test_send_activation_email_includes_code_and_activation_url(send_email):
    send_activation_email(
        recipient="teacher@example.com",
        full_name="Teacher Example",
        activation_code="ABCD1234",
        activation_url="https://pomsom.example/activate/",
    )

    params = send_email.call_args.args[0]
    assert params["to"] == ["teacher@example.com"]
    assert params["from"] == "POMSOM <noreply@example.com>"
    assert "ABCD1234" in params["text"]
    assert "https://pomsom.example/activate/" in params["text"]
    assert "password" not in params["text"].lower()


@override_settings(RESEND_API_KEY="", RESEND_FROM_EMAIL="")
@patch("apps.accounts.adapters.email.resend.Emails.send")
def test_send_activation_email_requires_configuration(send_email):
    with pytest.raises(RuntimeError, match="not configured"):
        send_activation_email(
            recipient="teacher@example.com",
            full_name="Teacher Example",
            activation_code="ABCD1234",
            activation_url="https://pomsom.example/activate/",
        )

    send_email.assert_not_called()
