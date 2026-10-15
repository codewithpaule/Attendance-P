from dataclasses import dataclass
from typing import Protocol


@dataclass
class PasskeyRegistrationOptions:
    challenge: str
    user_id: str
    user_name: str
    display_name: str
    rp_id: str
    rp_name: str
    timeout: int = 60000


@dataclass
class PasskeyRegistrationResponse:
    credential_id: str
    client_data_json: str
    attestation_object: str
    label: str


@dataclass
class PasskeyAuthenticationOptions:
    challenge: str
    rp_id: str
    timeout: int = 60000
    allow_credentials: list[str] | None = None


@dataclass
class PasskeyAuthenticationResponse:
    credential_id: str
    signature: str
    authenticator_data: str
    client_data_json: str
    user_handle: str | None = None


class WebAuthnAdapter(Protocol):
    def generate_registration_options(
        self,
        user_id: str,
        user_name: str,
        display_name: str,
        rp_id: str,
        rp_name: str,
    ) -> PasskeyRegistrationOptions: ...

    def verify_registration_response(
        self,
        response: PasskeyRegistrationResponse,
        expected_challenge: str,
        expected_origin: str,
        expected_rp_id: str,
    ) -> tuple[str, int]: ...

    def generate_authentication_options(
        self,
        rp_id: str,
        allowed_credential_ids: list[str] | None = None,
    ) -> PasskeyAuthenticationOptions: ...

    def verify_authentication_response(
        self,
        response: PasskeyAuthenticationResponse,
        expected_challenge: str,
        expected_origin: str,
        expected_rp_id: str,
        public_key: str,
        current_sign_count: int,
    ) -> int: ...
