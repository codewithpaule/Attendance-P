import ast
import base64
import codecs
import secrets

from webauthn import (
    generate_authentication_options,
    generate_registration_options,
    verify_authentication_response,
    verify_registration_response,
)
from webauthn.helpers import (
    parse_authentication_credential_json,
    parse_registration_credential_json,
)

from apps.accounts.domain.webauthn import (
    PasskeyAuthenticationOptions,
    PasskeyAuthenticationResponse,
    PasskeyRegistrationOptions,
    PasskeyRegistrationResponse,
    WebAuthnAdapter,
)


def _encode_challenge(challenge: bytes) -> str:
    return base64.urlsafe_b64encode(challenge).rstrip(b"=").decode("ascii")


def _decode_challenge(challenge: str) -> bytes:
    padded = challenge + "=" * (-len(challenge) % 4)
    return base64.urlsafe_b64decode(padded)


def _encode_public_key(public_key: str | bytes) -> str:
    if isinstance(public_key, str):
        public_key = public_key.encode("utf-8")
    return base64.urlsafe_b64encode(public_key).rstrip(b"=").decode("ascii")


def _decode_public_key(public_key: str | bytes) -> bytes:
    if isinstance(public_key, bytes):
        return public_key

    if not public_key:
        return b""

    value = str(public_key).strip()

    if value.startswith(("b'", 'b"')):
        try:
            return ast.literal_eval(value)
        except (ValueError, SyntaxError):
            pass

    try:
        padded = value + "=" * (-len(value) % 4)
        decoded = base64.urlsafe_b64decode(padded)
        if decoded:
            return decoded
    except (TypeError, ValueError):
        pass

    try:
        escaped = codecs.decode(value, "unicode_escape")
        return escaped.encode("latin1")
    except (TypeError, UnicodeDecodeError, ValueError):
        pass

    return value.encode("latin1")


class WebAuthnAdapterImpl(WebAuthnAdapter):
    def __init__(self, rp_id: str, rp_name: str, origin: str):
        self.rp_id = rp_id
        self.rp_name = rp_name
        self.origin = origin

    def generate_registration_options(
        self,
        user_id: str,
        user_name: str,
        display_name: str,
        rp_id: str,
        rp_name: str,
    ) -> PasskeyRegistrationOptions:
        challenge = secrets.token_bytes(32)
        options = generate_registration_options(
            rp_id=rp_id,
            rp_name=rp_name,
            user_id=user_id.encode("utf-8"),
            user_name=user_name,
            user_display_name=display_name,
            challenge=challenge,
        )
        return PasskeyRegistrationOptions(
            challenge=_encode_challenge(challenge),
            user_id=user_id,
            user_name=user_name,
            display_name=display_name,
            rp_id=rp_id,
            rp_name=rp_name,
            timeout=options.timeout,
        )

    def verify_registration_response(
        self,
        response: PasskeyRegistrationResponse,
        expected_challenge: str,
        expected_origin: str,
        expected_rp_id: str,
    ) -> tuple[str, int]:
        credential = parse_registration_credential_json(
            {
                "id": response.credential_id,
                "rawId": response.credential_id,
                "response": {
                    "clientDataJSON": response.client_data_json,
                    "attestationObject": response.attestation_object,
                },
                "type": "public-key",
            }
        )
        verification = verify_registration_response(
            credential=credential,
            expected_challenge=_decode_challenge(expected_challenge),
            expected_origin=expected_origin,
            expected_rp_id=expected_rp_id,
        )
        return _encode_public_key(verification.credential_public_key), verification.sign_count

    def generate_authentication_options(
        self,
        rp_id: str,
        allowed_credential_ids: list[str] | None = None,
    ) -> PasskeyAuthenticationOptions:
        challenge = secrets.token_bytes(32)
        options = generate_authentication_options(
            rp_id=rp_id,
            challenge=challenge,
            allow_credentials=allowed_credential_ids,
        )
        return PasskeyAuthenticationOptions(
            challenge=_encode_challenge(challenge),
            rp_id=rp_id,
            timeout=options.timeout,
            allow_credentials=allowed_credential_ids,
        )

    def verify_authentication_response(
        self,
        response: PasskeyAuthenticationResponse,
        expected_challenge: str,
        expected_origin: str,
        expected_rp_id: str,
        public_key: str,
        current_sign_count: int,
    ) -> int:
        credential = parse_authentication_credential_json(
            {
                "id": response.credential_id,
                "rawId": response.credential_id,
                "response": {
                    "clientDataJSON": response.client_data_json,
                    "authenticatorData": response.authenticator_data,
                    "signature": response.signature,
                    "userHandle": response.user_handle,
                },
                "type": "public-key",
            }
        )
        verification = verify_authentication_response(
            credential=credential,
            expected_challenge=_decode_challenge(expected_challenge),
            expected_origin=expected_origin,
            expected_rp_id=expected_rp_id,
            credential_public_key=_decode_public_key(public_key),
            credential_current_sign_count=current_sign_count,
        )
        return verification.new_sign_count
