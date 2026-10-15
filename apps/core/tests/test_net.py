from django.test import RequestFactory, TestCase, override_settings

from apps.core.net import get_client_ip


class TestGetClientIP(TestCase):
    def test_get_client_ip_from_vercel_header(self):
        """Test client IP from Vercel header when BEHIND_VERCEL is True."""
        with override_settings(BEHIND_VERCEL=True):
            factory = RequestFactory()
            request = factory.get("/")
            request.META["HTTP_X_VERCEL_IP_ADDRESS"] = "203.0.113.42"

            ip = get_client_ip(request)
            self.assertEqual(ip, "203.0.113.42")

    def test_get_client_ip_from_remote_addr(self):
        """Test client IP from REMOTE_ADDR when BEHIND_VERCEL is False."""
        with override_settings(BEHIND_VERCEL=False):
            factory = RequestFactory()
            request = factory.get("/")
            request.META["REMOTE_ADDR"] = "198.51.100.23"

            ip = get_client_ip(request)
            self.assertEqual(ip, "198.51.100.23")

    def test_get_client_ip_fallback_to_remote_addr(self):
        """Test fallback to REMOTE_ADDR when Vercel header is missing."""
        with override_settings(BEHIND_VERCEL=True):
            factory = RequestFactory()
            request = factory.get("/")
            request.META["REMOTE_ADDR"] = "192.0.2.1"

            ip = get_client_ip(request)
            self.assertEqual(ip, "192.0.2.1")

    def test_get_client_ip_defaults_to_localhost(self):
        """Test default to localhost when no IP is available."""
        with override_settings(BEHIND_VERCEL=False):
            factory = RequestFactory()
            request = factory.get("/")

            ip = get_client_ip(request)
            self.assertEqual(ip, "127.0.0.1")
