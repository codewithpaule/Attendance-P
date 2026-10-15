
from django.urls import path

from apps.accounts.web.views import activate_view, login_view, passkey_management

urlpatterns = [
    path("login/", login_view, name="login"),
    path("activate/", activate_view, name="activate"),
    path("passkeys/", passkey_management, name="passkey_management"),
]
