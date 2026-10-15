from django.db import models

from apps.academics.models import Course
from apps.accounts.models import User
from apps.core.models import BaseModel


class AttendanceRiskState(BaseModel):
    class Level(models.TextChoices):
        SAFE = "SAFE", "Safe"
        WARNING = "WARNING", "Warning"
        CRITICAL = "CRITICAL", "Critical"

    student = models.ForeignKey(User, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    level = models.CharField(max_length=20, choices=Level.choices, default=Level.SAFE)
    percentage = models.FloatField(default=0.0)
    can_still_miss = models.IntegerField(default=0)
    evaluated_at = models.DateTimeField()
    last_alert_level = models.CharField(max_length=20, null=True, blank=True)
    last_alert_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "alerts_attendance_risk_state"
        unique_together = [["student", "course"]]


class Notification(BaseModel):
    class Kind(models.TextChoices):
        ATTENDANCE_RISK = "ATTENDANCE_RISK", "Attendance Risk"
        SESSION_REMINDER = "SESSION_REMINDER", "Session Reminder"

    class Channel(models.TextChoices):
        IN_APP = "IN_APP", "In App"
        EMAIL = "EMAIL", "Email"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        SENT = "SENT", "Sent"
        FAILED = "FAILED", "Failed"
        SKIPPED = "SKIPPED", "Skipped"

    recipient = models.ForeignKey(User, on_delete=models.CASCADE)
    kind = models.CharField(max_length=50, choices=Kind.choices)
    channel = models.CharField(max_length=20, choices=Channel.choices)
    payload = models.JSONField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    dedupe_key = models.CharField(max_length=255, unique=True)
    attempts = models.IntegerField(default=0)
    last_error = models.TextField(blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "alerts_notification"
