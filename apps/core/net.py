from django.conf import settings
from django.http import HttpRequest


def get_client_ip(request: HttpRequest) -> str:
    """Get the real client IP address.

    When BEHIND_VERCEL is True, reads the Vercel-provided header.
    Otherwise, uses REMOTE_ADDR.

    Args:
        request: The HTTP request object

    Returns:
        The client IP address as a string
    """
    if getattr(settings, "BEHIND_VERCEL", False):
        # Vercel provides the real client IP in X-Vercel-IP-Address
        # This header is set by Vercel and cannot be spoofed
        ip = request.headers.get("X-Vercel-IP-Address")
        if ip:
            return ip

    # Fallback to REMOTE_ADDR (development, other proxies)
    return request.META.get("REMOTE_ADDR", "127.0.0.1")
