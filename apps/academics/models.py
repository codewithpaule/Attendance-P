from django.db import models

from apps.accounts.models import User
from apps.core.models import BaseModel


class Term(BaseModel):
    name = models.CharField(max_length=100)
    starts_on = models.DateField()
    ends_on = models.DateField()
    is_current = models.BooleanField(default=False)

    class Meta:
        db_table = "academics_term"


class Room(BaseModel):
    name = models.CharField(max_length=100, unique=True)
    latitude = models.DecimalField(max_digits=10, decimal_places=7)
    longitude = models.DecimalField(max_digits=10, decimal_places=7)
    radius_m = models.IntegerField()

    class Meta:
        db_table = "academics_room"


class Course(BaseModel):
    code = models.CharField(max_length=50)
    title = models.CharField(max_length=255)
    term = models.ForeignKey(Term, on_delete=models.CASCADE)
    teacher = models.ForeignKey(User, on_delete=models.CASCADE, related_name="taught_courses")
    default_room = models.ForeignKey(Room, on_delete=models.PROTECT, null=True, blank=True)
    planned_sessions = models.IntegerField(default=1)

    class Meta:
        db_table = "academics_course"
        unique_together = [["code", "term"]]


class Enrollment(BaseModel):
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name="enrollments")

    class Meta:
        db_table = "academics_enrollment"
        unique_together = [["course", "student"]]


class AdvisorAssignment(BaseModel):
    advisor = models.ForeignKey(User, on_delete=models.CASCADE, related_name="advisees")
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name="advisors")

    class Meta:
        db_table = "academics_advisor_assignment"
        unique_together = [["advisor", "student"]]


class EligibilityPolicy(BaseModel):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, null=True, blank=True)
    threshold_pct = models.IntegerField(default=75)
    warning_buffer_pct = models.IntegerField(default=8)
    trend_window = models.IntegerField(default=4)
    min_sessions_before_alert = models.IntegerField(default=3)
    alert_cooldown_days = models.IntegerField(default=7)

    class Meta:
        db_table = "academics_eligibility_policy"
