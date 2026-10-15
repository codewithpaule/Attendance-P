from typing import Protocol

from django.core.signing import BadSignature, TimestampSigner


class QRTokenError(Exception):
    """Raised when QR token verification fails."""


class QRTokenAdapter(Protocol):
    def generate_token(self, session_id: str) -> str: ...

    def verify_token(self, token: str, session_id: str) -> bool: ...


class DjangoQRTokenAdapter:
    def __init__(self, salt: str = "attendance-qr-token", max_age_seconds: int = 20):
        self.signer = TimestampSigner(salt=salt)
        self.max_age_seconds = max_age_seconds

    def generate_token(self, session_id: str) -> str:
        return self.signer.sign(session_id)

    def verify_token(self, token: str, session_id: str) -> bool:
        try:
            decoded = self.signer.unsign(token, max_age=self.max_age_seconds)
            return decoded == session_id
        except BadSignature as err:
            raise QRTokenError("Invalid token signature") from err
        except Exception as err:
            raise QRTokenError("Token verification failed") from err
