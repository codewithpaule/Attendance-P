import resend
from django.conf import settings


def send_activation_email(
    recipient: str,
    full_name: str,
    activation_code: str,
    activation_url: str,
) -> None:
    if not settings.RESEND_API_KEY or not settings.RESEND_FROM_EMAIL:
        raise RuntimeError("Activation email is not configured.")

    resend.api_key = settings.RESEND_API_KEY
    resend.Emails.send(
        {
            "from": settings.RESEND_FROM_EMAIL,
            "to": [recipient],
            "subject": "Activate your POMSOM account",
            "text": (
                f"Hello {full_name},\n\n"
                "Your POMSOM account is ready. Use the activation code below to register "
                "your passkey and activate your account.\n\n"
                f"Activation code: {activation_code}\n"
                f"Activation page: {activation_url}\n\n"
                "The code expires in 7 days. You do not need a student number to activate "
                "a teacher account."
            ),
        }
    )
