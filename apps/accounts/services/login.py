from django.contrib.auth import login
from django.db import transaction

from apps.accounts.domain.webauthn import PasskeyAuthenticationResponse
from apps.accounts.exceptions import BadRequestError
from apps.accounts.models import User
from apps.accounts.selectors.functions import get_active_passkey
from apps.audit.services.record import record
from apps.core.clock import Clock


@transaction.atomic
def login_with_passkey(
    request,
    credential_id: str,
    response: PasskeyAuthenticationResponse,
    expected_challenge: str,
    clock: Clock,
    webauthn_adapter,
    origin: str,
) -> User:
    """Authenticate user with passkey."""
    credential = get_active_passkey(credential_id)
    if not credential:
        raise BadRequestError("PASSKEY_INVALID", "Invalid credential")

    user = credential.user
    if not user.is_active:
        raise BadRequestError("USER_INACTIVE", "User account is not active")

    new_sign_count = webauthn_adapter.verify_authentication_response(
        response=response,
        expected_challenge=expected_challenge,
        expected_origin=origin,
        expected_rp_id=webauthn_adapter.rp_id,
        public_key=credential.public_key,
        current_sign_count=credential.sign_count,
    )

    credential.sign_count = new_sign_count
    credential.last_used_at = clock.now()
    credential.save()

    login(request, user)

    record(
        actor=user,
        action="USER_LOGIN",
        target_type="User",
        target_id=str(user.id),
        ip=request.META.get("REMOTE_ADDR"),
    )

    return user
