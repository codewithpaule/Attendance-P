from datetime import timedelta

from django.db import transaction

from apps.accounts.domain.password import generate_activation_code, hash_code
from apps.accounts.models import ActivationCode, User
from apps.core.clock import Clock


@transaction.atomic
def issue_activation_code(user: User, clock: Clock) -> str:
    if user.is_active:
        raise ValueError("Cannot issue an activation code for an active account.")

    now = clock.now()
    ActivationCode.objects.filter(
        user=user,
        purpose=ActivationCode.Purpose.ACTIVATION,
        used_at__isnull=True,
    ).update(used_at=now)

    code = generate_activation_code()
    ActivationCode.objects.create(
        user=user,
        purpose=ActivationCode.Purpose.ACTIVATION,
        code_hash=hash_code(code),
        expires_at=now + timedelta(days=7),
    )
    return code
