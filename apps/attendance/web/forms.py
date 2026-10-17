from django import forms
from django.utils import timezone

from apps.academics.models import Course


class ClassSessionForm(forms.Form):
    course = forms.ModelChoiceField(queryset=Course.objects.none())
    scheduled_start_at = forms.DateTimeField(
        input_formats=["%Y-%m-%dT%H:%M"],
        widget=forms.DateTimeInput(
            format="%Y-%m-%dT%H:%M",
            attrs={"type": "datetime-local"},
        ),
    )
    scheduled_end_at = forms.DateTimeField(
        input_formats=["%Y-%m-%dT%H:%M"],
        widget=forms.DateTimeInput(
            format="%Y-%m-%dT%H:%M",
            attrs={"type": "datetime-local"},
        ),
    )

    def __init__(self, *args, teacher, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["course"].queryset = Course.objects.filter(
            teacher=teacher,
            default_room__isnull=False,
        ).select_related("default_room").order_by("code")

    def clean(self):
        cleaned_data = super().clean()
        start_at = cleaned_data.get("scheduled_start_at")
        end_at = cleaned_data.get("scheduled_end_at")
        if start_at and end_at:
            if start_at <= timezone.now():
                self.add_error("scheduled_start_at", "Choose a future class start time.")
            if end_at <= start_at:
                self.add_error("scheduled_end_at", "Class end time must be after its start time.")
        return cleaned_data
