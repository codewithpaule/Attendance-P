import base64
from types import SimpleNamespace
from unittest.mock import patch

from apps.accounts.adapters.webauthn import WebAuthnAdapterImpl
from apps.accounts.domain.webauthn import (
    PasskeyAuthenticationResponse,
    PasskeyRegistrationResponse,
)


def encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


@patch("apps.accounts.adapters.webauthn.verify_registration_response")
def test_registration_verification_parses_webauthn_v3_credential(mock_verify):
    mock_verify.return_value = SimpleNamespace(credential_public_key=b"\xa2\x01\x02", sign_count=4)
    adapter = WebAuthnAdapterImpl(
        rp_id="example.test", rp_name="POMSOM", origin="https://example.test"
    )
    response = PasskeyRegistrationResponse(
        credential_id=encode(b"credential"),
        client_data_json=encode(b"client-data"),
        attestation_object=encode(b"attestation"),
        label="Phone",
    )

    result = adapter.verify_registration_response(
        response=response,
        expected_challenge=encode(b"challenge"),
        expected_origin=adapter.origin,
        expected_rp_id=adapter.rp_id,
    )

    assert result == (encode(b"\xa2\x01\x02"), 4)
    credential = mock_verify.call_args.kwargs["credential"]
    assert credential.raw_id == b"credential"
    assert credential.response.client_data_json == b"client-data"
    assert credential.response.attestation_object == b"attestation"
    assert mock_verify.call_args.kwargs["expected_challenge"] == b"challenge"


@patch("apps.accounts.adapters.webauthn.verify_authentication_response")
def test_authentication_verification_decodes_stored_public_key(mock_verify):
    mock_verify.return_value = SimpleNamespace(new_sign_count=5)
    adapter = WebAuthnAdapterImpl(
        rp_id="example.test", rp_name="POMSOM", origin="https://example.test"
    )
    response = PasskeyAuthenticationResponse(
        credential_id=encode(b"credential"),
        client_data_json=encode(b"client-data"),
        authenticator_data=encode(b"authenticator-data"),
        signature=encode(b"signature"),
        user_handle=encode(b"user-handle"),
    )
    stored_public_key = encode(b"\xa2\x01\x02")

    result = adapter.verify_authentication_response(
        response=response,
        expected_challenge=encode(b"challenge"),
        expected_origin=adapter.origin,
        expected_rp_id=adapter.rp_id,
        public_key=stored_public_key,
        current_sign_count=4,
    )

    assert result == 5
    assert mock_verify.call_args.kwargs["credential_public_key"] == b"\xa2\x01\x02"


@patch("apps.accounts.adapters.webauthn.verify_authentication_response")
def test_authentication_verification_decodes_legacy_python_bytes_repr(mock_verify):
    mock_verify.return_value = SimpleNamespace(new_sign_count=7)
    adapter = WebAuthnAdapterImpl(
        rp_id="example.test", rp_name="POMSOM", origin="https://example.test"
    )
    response = PasskeyAuthenticationResponse(
        credential_id=encode(b"credential"),
        client_data_json=encode(b"client-data"),
        authenticator_data=encode(b"authenticator-data"),
        signature=encode(b"signature"),
        user_handle=encode(b"user-handle"),
    )

    result = adapter.verify_authentication_response(
        response=response,
        expected_challenge=encode(b"challenge"),
        expected_origin=adapter.origin,
        expected_rp_id=adapter.rp_id,
        public_key="b'\\xa2\\x01\\x02'",
        current_sign_count=4,
    )

    assert result == 7
    assert mock_verify.call_args.kwargs["credential_public_key"] == b"\xa2\x01\x02"


@patch("apps.accounts.adapters.webauthn.verify_authentication_response")
def test_authentication_verification_parses_webauthn_v3_credential(mock_verify):
    mock_verify.return_value = SimpleNamespace(new_sign_count=5)
    adapter = WebAuthnAdapterImpl(
        rp_id="example.test", rp_name="POMSOM", origin="https://example.test"
    )
    response = PasskeyAuthenticationResponse(
        credential_id=encode(b"credential"),
        client_data_json=encode(b"client-data"),
        authenticator_data=encode(b"authenticator-data"),
        signature=encode(b"signature"),
        user_handle=encode(b"user-handle"),
    )

    result = adapter.verify_authentication_response(
        response=response,
        expected_challenge=encode(b"challenge"),
        expected_origin=adapter.origin,
        expected_rp_id=adapter.rp_id,
        public_key="public-key",
        current_sign_count=4,
    )

    assert result == 5
    credential = mock_verify.call_args.kwargs["credential"]
    assert credential.raw_id == b"credential"
    assert credential.response.client_data_json == b"client-data"
    assert credential.response.authenticator_data == b"authenticator-data"
    assert credential.response.signature == b"signature"
    assert credential.response.user_handle == b"user-handle"
    assert mock_verify.call_args.kwargs["expected_challenge"] == b"challenge"
