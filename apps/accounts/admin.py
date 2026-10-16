from django import forms
from django.contrib import admin, messages
from django.urls import reverse

from apps.accounts.adapters.email import send_activation_email
from apps.accounts.models import User
from apps.accounts.services.activation_codes import issue_activation_code
from apps.core.clock import DefaultClock


class AccountAdminForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("email", "full_name", "role", "student_number")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        role_choices = [choice for choice in User.Role.choices if choice[0] != User.Role.ADMIN]
        if self.instance.pk and self.instance.role == User.Role.ADMIN:
            role_choices.append((User.Role.ADMIN, User.Role.ADMIN.label))
        self.fields["role"].choices = role_choices

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("role") == User.Role.STUDENT and not cleaned_data.get("student_number"):
            self.add_error("student_number", "A student number is required for student accounts.")
        return cleaned_data


@admin.register(User)
class AccountAdmin(admin.ModelAdmin):
    form = AccountAdminForm
    list_display = ("email", "full_name", "role", "student_number", "is_active", "is_staff")
    list_filter = ("role", "is_active", "is_staff")
    search_fields = ("email", "full_name", "student_number")
    ordering = ("email",)
    actions = ("resend_activation_emails",)

    def get_fields(self, _request, obj=None):
        fields = ["email", "full_name", "role", "student_number"]
        if obj:
            fields.extend(["is_active", "is_staff", "created_at", "updated_at"])
        return fields

    def get_readonly_fields(self, _request, obj=None):
        return ("created_at", "updated_at") if obj else ()

    def save_model(self, request, obj, form, change):
        is_new = obj._state.adding
        if is_new:
            obj.set_unusable_password()
        super().save_model(request, obj, form, change)

        if is_new:
            code = issue_activation_code(obj, DefaultClock())
            self._send_activation_email(request, obj, code)

    @admin.action(description="Resend activation email")
    def resend_activation_emails(self, request, queryset):
        sent = 0
        failed = 0
        skipped = 0
        for user in queryset:
            if user.is_active:
                skipped += 1
                continue
            code = issue_activation_code(user, DefaultClock())
            if self._send_activation_email(request, user, code, notify=False):
                sent += 1
            else:
                failed += 1

        self.message_user(
            request,
            f"Activation emails sent: {sent}. Failed: {failed}. Already active: {skipped}.",
            level=messages.SUCCESS if not failed else messages.WARNING,
        )

    def _send_activation_email(self, request, user, code, notify=True) -> bool:
        try:
            send_activation_email(
                recipient=user.email,
                full_name=user.full_name,
                activation_code=code,
                activation_url=request.build_absolute_uri(reverse("activate")),
            )
        except Exception:
            self.message_user(
                request,
                f"Account {user.email} was saved, but the activation email failed. "
                "Check email configuration and use the Resend activation email action.",
                level=messages.ERROR,
            )
            return False

        if notify:
            self.message_user(
                request,
                f"Activation instructions were emailed to {user.email}.",
                level=messages.SUCCESS,
            )
        return True
