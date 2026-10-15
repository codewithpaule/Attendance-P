import secrets

from webauthn import (
    generate_authentication_options,
    generate_registration_options,
    verify_authentication_response,
    verify_registration_response,
)
from webauthn.helpers.structs import (
    AuthenticationCredential,
    PublicKeyCredentialUserEntity,
    RegistrationCredential,
)

from apps.accounts.domain.webauthn import (
    PasskeyAuthenticationOptions,
    PasskeyAuthenticationResponse,
    PasskeyRegistrationOptions,
    PasskeyRegistrationResponse,
    WebAuthnAdapter,
)


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
        challenge = secrets.token_urlsafe(32)
        options = generate_registration_options(
            rp_id=rp_id,
            rp_name=rp_name,
            user=PublicKeyCredentialUserEntity(
                id=user_id.encode("utf-8"),
                name=user_name,
                display_name=display_name,
            ),
            challenge=challenge,
        )
        return PasskeyRegistrationOptions(
            challenge=challenge,
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
        credential = RegistrationCredential.parse_raw(
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
            expected_challenge=expected_challenge,
            expected_origin=expected_origin,
            expected_rp_id=expected_rp_id,
        )
        return verification.credential_public_key, verification.sign_count

    def generate_authentication_options(
        self,
        rp_id: str,
        allowed_credential_ids: list[str] | None = None,
    ) -> PasskeyAuthenticationOptions:
        challenge = secrets.token_urlsafe(32)
        options = generate_authentication_options(
            rp_id=rp_id,
            challenge=challenge,
            allow_credentials=allowed_credential_ids,
        )
        return PasskeyAuthenticationOptions(
            challenge=challenge,
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
        credential = AuthenticationCredential.parse_raw(
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
            expected_challenge=expected_challenge,
            expected_origin=expected_origin,
            expected_rp_id=expected_rp_id,
            credential_public_key=public_key,
            credential_current_sign_count=current_sign_count,
        )
        return verification.new_sign_count
