
from django.db import transaction

from apps.accounts.domain.webauthn import PasskeyRegistrationResponse
from apps.accounts.exceptions import BadRequestError, NotFoundError
from apps.accounts.models import PasskeyCredential, User
from apps.accounts.selectors.functions import get_passkey
from apps.audit.services.record import record
from apps.core.clock import Clock


@transaction.atomic
def register_passkey(
    user: User,
    response: PasskeyRegistrationResponse,
    expected_challenge: str,
    label: str,
    clock: Clock,
    webauthn_adapter,
    origin: str,
) -> PasskeyCredential:
    """Register a new passkey for a user."""
    if not user.is_active:
        raise BadRequestError("User account is not active")

    public_key, sign_count = webauthn_adapter.verify_registration_response(
        response=response,
        expected_challenge=expected_challenge,
        expected_origin=origin,
        expected_rp_id=webauthn_adapter.rp_id,
    )

    credential = user.passkey_credentials.create(
        credential_id=response.credential_id,
        public_key=public_key,
        sign_count=sign_count,
        label=label,
    )

    record(
        actor=user,
        action="PASSKEY_REGISTERED",
        target_type="PasskeyCredential",
        target_id=str(credential.id),
    )

    return credential


@transaction.atomic
def revoke_passkey(user: User, credential_id: str, clock: Clock) -> None:
    """Revoke a passkey."""
    credential = get_passkey(credential_id, user)
    if not credential:
        raise NotFoundError("Passkey not found")

    credential.revoked_at = clock.now()
    credential.save()

    record(
        actor=user,
        action="PASSKEY_REVOKED",
        target_type="PasskeyCredential",
        target_id=str(credential.id),
    )
