import pytest
from django.contrib.auth import SESSION_KEY
from django.urls import reverse

from apps.accounts.models import User


@pytest.mark.django_db
def test_logout_clears_session_and_redirects_to_login(client):
    user = User.objects.create_user(
        email="teacher@example.com",
        password="test-password",
        full_name="Teacher Example",
        role=User.Role.TEACHER,
        is_active=True,
    )
    client.force_login(user)

    response = client.post(reverse("logout"))

    assert response.status_code == 302
    assert response.url == reverse("login")
    assert SESSION_KEY not in client.session


@pytest.mark.django_db
def test_logout_rejects_get(client):
    response = client.get(reverse("logout"))

    assert response.status_code == 405