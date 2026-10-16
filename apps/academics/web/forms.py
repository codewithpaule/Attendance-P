from django import forms

from apps.academics.models import Room


class ClassroomLocationForm(forms.Form):
    room_name = forms.CharField(max_length=100, label="Classroom name")
    latitude = forms.DecimalField(
        max_digits=10,
        decimal_places=7,
        min_value=-90,
        max_value=90,
        widget=forms.HiddenInput,
    )
    longitude = forms.DecimalField(
        max_digits=10,
        decimal_places=7,
        min_value=-180,
        max_value=180,
        widget=forms.HiddenInput,
    )
    radius_m = forms.IntegerField(min_value=10, max_value=2000, widget=forms.HiddenInput)

    def __init__(self, *args, room: Room | None = None, room_is_shared: bool = False, **kwargs):
        super().__init__(*args, **kwargs)
        self.room = room
        self.room_is_shared = room_is_shared

    def clean_room_name(self) -> str:
        room_name = self.cleaned_data["room_name"]
        if self.room_is_shared and room_name.casefold() == self.room.name.casefold():
            raise forms.ValidationError(
                "This classroom is shared with another course. Choose a distinct name to set a separate location."
            )
        rooms = Room.objects.filter(name__iexact=room_name)
        if self.room:
            rooms = rooms.exclude(pk=self.room.pk)
        if rooms.exists():
            raise forms.ValidationError("A classroom with this name already exists.")
        return room_name
