from apps.accounts.models import PasskeyCredential, User


def get_user_by_email(email: str) -> User | None:
    return User.objects.filter(email__iexact=email).first()


def get_user_by_student_number(student_number: str) -> User | None:
    return User.objects.filter(student_number=student_number).first()


def list_passkeys(user: User) -> list[PasskeyCredential]:
    return list(user.passkey_credentials.filter(revoked_at__isnull=True).order_by("-created_at"))


def get_passkey(credential_id: str, user: User) -> PasskeyCredential | None:
    return user.passkey_credentials.filter(
        credential_id=credential_id, revoked_at__isnull=True
    ).first()


def get_active_passkey(credential_id: str) -> PasskeyCredential | None:
    return (
        PasskeyCredential.objects.filter(credential_id=credential_id, revoked_at__isnull=True)
        .select_related("user")
        .first()
    )
