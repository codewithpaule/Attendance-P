from datetime import timedelta

from django.db import transaction

from apps.accounts.domain.password import (
    generate_activation_code,
    hash_code,
    verify_code,
)
from apps.accounts.exceptions import BadRequestError, NotFoundError
from apps.accounts.models import ActivationCode, User
from apps.accounts.selectors.functions import get_user_by_student_number
from apps.audit.services.record import record
from apps.core.clock import Clock


@transaction.atomic
def issue_recovery_code(
    student_number: str,
    issuer: User,
    clock: Clock,
) -> str:
    """Issue a single-use recovery code for a user who lost all devices."""
    user = get_user_by_student_number(student_number)
    if not user:
        raise NotFoundError("User not found")

    if issuer.role not in (User.Role.ADMIN, User.Role.ADVISOR):
        from apps.core.exceptions import PermissionDeniedError

        raise PermissionDeniedError(
            code="PERMISSION_DENIED",
            message="Only admins and advisors can issue recovery codes",
        )

    code = generate_activation_code()
    ActivationCode.objects.create(
        user=user,
        purpose=ActivationCode.Purpose.RECOVERY,
        code_hash=hash_code(code),
        expires_at=clock.now() + timedelta(hours=24),
    )

    record(
        actor=issuer,
        action="RECOVERY_CODE_ISSUED",
        target_type="User",
        target_id=str(user.id),
    )

    return code


@transaction.atomic
def use_recovery_code(
    student_number: str,
    code: str,
    new_password: str,
    clock: Clock,
) -> User:
    """Use a recovery code to reset password and issue a new activation code."""
    user = get_user_by_student_number(student_number)
    if not user:
        raise NotFoundError("User not found")

    recovery_code = (
        ActivationCode.objects.filter(
            user=user,
            purpose=ActivationCode.Purpose.RECOVERY,
            used_at__isnull=True,
        )
        .order_by("-created_at")
        .first()
    )

    if not recovery_code:
        raise BadRequestError("No valid recovery code found")

    if recovery_code.expires_at < clock.now():
        raise BadRequestError("Recovery code expired")

    if not verify_code(code, recovery_code.code_hash):
        raise BadRequestError("Invalid recovery code")

    user.set_password(new_password)
    user.save()

    recovery_code.used_at = clock.now()
    recovery_code.save()

    record(
        actor=user,
        action="RECOVERY_CODE_USED",
        target_type="User",
        target_id=str(user.id),
    )

    return user
