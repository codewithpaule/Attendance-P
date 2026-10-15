from django.contrib import admin

from apps.academics.models import (
    AdvisorAssignment,
    Course,
    EligibilityPolicy,
    Enrollment,
    Room,
    Term,
)


@admin.register(Term)
class TermAdmin(admin.ModelAdmin):
    list_display = ["name", "starts_on", "ends_on", "is_current"]
    list_filter = ["is_current"]
    search_fields = ["name"]


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ["name", "latitude", "longitude", "radius_m"]
    search_fields = ["name"]


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ["code", "title", "term", "teacher", "default_room", "planned_sessions"]
    list_filter = ["term"]
    search_fields = ["code", "title"]
    raw_id_fields = ["teacher", "default_room"]


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ["course", "student"]
    list_filter = ["course"]
    raw_id_fields = ["course", "student"]


@admin.register(AdvisorAssignment)
class AdvisorAssignmentAdmin(admin.ModelAdmin):
    list_display = ["advisor", "student"]
    raw_id_fields = ["advisor", "student"]


@admin.register(EligibilityPolicy)
class EligibilityPolicyAdmin(admin.ModelAdmin):
    list_display = [
        "course",
        "threshold_pct",
        "warning_buffer_pct",
        "trend_window",
        "min_sessions_before_alert",
        "alert_cooldown_days",
    ]
    list_filter = ["course"]
    raw_id_fields = ["course"]
