import secrets
import string


def generate_activation_code() -> str:
    """Generate a random 8-character activation code."""
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(8))


def hash_code(code: str) -> str:
    """Hash a code using Django's password hasher."""
    from django.contrib.auth.hashers import make_password

    return make_password(code)


def verify_code(code: str, hashed: str) -> bool:
    """Verify a code against its hash."""
    from django.contrib.auth.hashers import check_password

    return check_password(code, hashed)
