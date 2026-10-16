from datetime import timedelta

from django import forms
from django.contrib import admin, messages

from apps.accounts.domain.password import generate_activation_code, hash_code
from apps.accounts.models import ActivationCode, User
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
            code = generate_activation_code()
            ActivationCode.objects.create(
                user=obj,
                purpose=ActivationCode.Purpose.ACTIVATION,
                code_hash=hash_code(code),
                expires_at=DefaultClock().now() + timedelta(days=7),
            )
            self.message_user(
                request,
                f"One-time activation code for {obj.email}: {code}",
                level=messages.SUCCESS,
            )
