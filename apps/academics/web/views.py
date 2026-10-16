from decimal import Decimal, InvalidOperation

from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from apps.academics.models import Course
from apps.academics.selectors.functions import get_courses_for_teacher
from apps.academics.services.classroom import save_classroom_location
from apps.academics.web.forms import ClassroomLocationForm
from apps.accounts.models import User


@login_required(login_url="login")
@require_http_methods(["GET", "POST"])
def classroom_map_view(request):
    if request.user.role != User.Role.TEACHER:
        return HttpResponseForbidden("Teacher access is required.")

    courses = get_courses_for_teacher(request.user)
    course_id = (
        request.POST.get("course_id") if request.method == "POST" else request.GET.get("course")
    )
    if course_id and not any(str(item.id) == course_id for item in courses):
        return HttpResponseForbidden("You cannot edit this course.")
    if not courses:
        return render(request, "academics/classroom_map.html", {"courses": courses})

    course = next((item for item in courses if str(item.id) == course_id), courses[0])
    room = course.default_room
    room_is_shared = bool(
        room and Course.objects.filter(default_room=room).exclude(pk=course.pk).exists()
    )

    if request.method == "POST":
        form = ClassroomLocationForm(request.POST, room=room, room_is_shared=room_is_shared)
        if form.is_valid():
            save_classroom_location(
                course_id=str(course.id),
                teacher=request.user,
                room_name=form.cleaned_data["room_name"],
                latitude=form.cleaned_data["latitude"],
                longitude=form.cleaned_data["longitude"],
                radius_m=form.cleaned_data["radius_m"],
            )
            return redirect(f"{reverse('classroom_map')}?course={course.id}")
    else:
        form = ClassroomLocationForm(
            initial={
                "room_name": room.name if room else f"{course.code} classroom",
                "latitude": room.latitude if room else "",
                "longitude": room.longitude if room else "",
                "radius_m": room.radius_m if room else 100,
            },
            room=room,
            room_is_shared=room_is_shared,
        )

    initial_latitude = room.latitude if room else Decimal("6.5244")
    initial_longitude = room.longitude if room else Decimal("3.3792")
    has_location = bool(room)
    radius = room.radius_m if room else 100
    if form.is_bound:
        try:
            latitude_value = form["latitude"].value()
            longitude_value = form["longitude"].value()
            radius_value = form["radius_m"].value()
            if latitude_value and longitude_value:
                initial_latitude = Decimal(latitude_value)
                initial_longitude = Decimal(longitude_value)
                has_location = True
            if radius_value:
                radius = int(radius_value)
        except (InvalidOperation, TypeError, ValueError):
            pass

    return render(
        request,
        "academics/classroom_map.html",
        {
            "courses": courses,
            "selected_course": course,
            "form": form,
            "map_latitude": initial_latitude,
            "map_longitude": initial_longitude,
            "has_location": has_location,
            "radius": radius,
        },
    )
