from django.db import transaction

from apps.accounts.domain.password import verify_code
from apps.accounts.exceptions import BadRequestError, ConflictError, NotFoundError
from apps.accounts.models import ActivationCode, User
from apps.accounts.selectors import get_user_by_email, get_user_by_student_number
from apps.audit.services.record import record
from apps.core.clock import Clock


@transaction.atomic
def activate_user(
    code: str,
    password: str,
    webauthn_response: dict,
    clock: Clock,
    webauthn_adapter,
    origin: str,
    email: str | None = None,
    student_number: str | None = None,
) -> User:
    """Activate an account using its email or legacy student number."""
    user = get_user_by_email(email) if email else get_user_by_student_number(student_number or "")
    if not user:
        raise NotFoundError("User not found")

    if user.is_active:
        raise ConflictError("User already activated")

    activation_code = (
        ActivationCode.objects.filter(
            user=user,
            purpose=ActivationCode.Purpose.ACTIVATION,
            used_at__isnull=True,
        )
        .order_by("-created_at")
        .first()
    )

    if not activation_code:
        raise BadRequestError("No valid activation code found")

    if activation_code.expires_at < clock.now():
        raise BadRequestError("Activation code expired")

    if not verify_code(code, activation_code.code_hash):
        raise BadRequestError("Invalid activation code")

    user.set_password(password)
    user.is_active = True
    user.activated_at = clock.now()
    user.save()

    activation_code.used_at = clock.now()
    activation_code.save()

    public_key, sign_count = webauthn_adapter.verify_registration_response(
        response=webauthn_response,
        expected_challenge=webauthn_response["challenge"],
        expected_origin=origin,
        expected_rp_id=webauthn_adapter.rp_id,
    )

    user.passkey_credentials.create(
        credential_id=webauthn_response["credential_id"],
        public_key=public_key,
        sign_count=sign_count,
        label="Default",
    )

    record(
        actor=user,
        action="USER_ACTIVATED",
        target_type="User",
        target_id=str(user.id),
    )

    return user
