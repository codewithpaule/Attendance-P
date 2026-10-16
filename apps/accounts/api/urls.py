from django.urls import path

from apps.accounts.api.views import (
    activate,
    import_users,
    issue_recovery_code,
    list_passkeys,
    login,
    login_begin,
    register_passkey_begin,
    register_passkey_begin_for_activation,
    register_passkey_complete,
    revoke_passkey,
    use_recovery_code,
)

urlpatterns = [
    path("auth/login/begin", login_begin, name="login_begin"),
    path("auth/login", login, name="login"),
    path("auth/activate", activate, name="activate"),
    path(
        "passkeys/register/begin",
        register_passkey_begin,
        name="register_passkey_begin",
    ),
    path(
        "passkeys/register/begin-activation",
        register_passkey_begin_for_activation,
        name="register_passkey_begin_for_activation",
    ),
    path("passkeys/register/complete", register_passkey_complete, name="register_passkey_complete"),
    path("passkeys/", list_passkeys, name="list_passkeys"),
    path("passkeys/<str:credential_id>/revoke", revoke_passkey, name="revoke_passkey"),
    path("recovery-codes/issue", issue_recovery_code, name="issue_recovery_code"),
    path("recovery-codes/use", use_recovery_code, name="use_recovery_code"),
    path("admin/import-users", import_users, name="import_users"),
]
