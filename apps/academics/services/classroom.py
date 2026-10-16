from decimal import Decimal

from django.db import transaction

from apps.academics.models import Course, Room
from apps.accounts.models import User
from apps.audit.services.record import record
from apps.core.exceptions import NotFoundError


@transaction.atomic
def save_classroom_location(
    course_id: str,
    teacher: User,
    room_name: str,
    latitude: Decimal,
    longitude: Decimal,
    radius_m: int,
) -> Room:
    course = (
        Course.objects.select_for_update()
        .filter(id=course_id, teacher=teacher)
        .select_related("default_room")
        .first()
    )
    if not course:
        raise NotFoundError("COURSE_NOT_FOUND", "Course not found")

    room = course.default_room
    shared_room = room and Course.objects.filter(default_room=room).exclude(pk=course.pk).exists()
    if room and not shared_room:
        room.name = room_name
        room.latitude = latitude
        room.longitude = longitude
        room.radius_m = radius_m
        room.save()
    else:
        room = Room.objects.create(
            name=room_name,
            latitude=latitude,
            longitude=longitude,
            radius_m=radius_m,
        )
        if not course.default_room or shared_room:
            course.default_room = room
            course.save(update_fields=["default_room", "updated_at"])

    record(
        actor=teacher,
        action="CLASSROOM_LOCATION_UPDATED",
        target_type="Room",
        target_id=str(room.id),
        metadata={"course_id": str(course.id), "radius_m": radius_m},
    )
    return room
