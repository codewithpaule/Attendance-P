from django.db import models

from apps.academics.models import Course, Room
from apps.accounts.models import PasskeyCredential, User
from apps.core.models import BaseModel


class ClassSession(BaseModel):
    class Status(models.TextChoices):
        SCHEDULED = "SCHEDULED", "Scheduled"
        OPEN = "OPEN", "Open"
        CLOSED = "CLOSED", "Closed"
        FINALIZED = "FINALIZED", "Finalized"

    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    room = models.ForeignKey(Room, on_delete=models.PROTECT)
    teacher = models.ForeignKey(User, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SCHEDULED)
    scheduled_start_at = models.DateTimeField(null=True, blank=True)
    scheduled_end_at = models.DateTimeField(null=True, blank=True)
    opened_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    finalized_at = models.DateTimeField(null=True, blank=True)
    checkin_window_minutes = models.IntegerField(default=15)
    headcount = models.IntegerField(null=True, blank=True)
    needs_audit = models.BooleanField(default=False)

    class Meta:
        db_table = "attendance_class_session"
        constraints = [
            models.UniqueConstraint(
                fields=["course"],
                condition=models.Q(status="OPEN"),
                name="unique_open_session_per_course",
            )
        ]


class CheckInAttempt(BaseModel):
    session = models.ForeignKey(ClassSession, on_delete=models.CASCADE)
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    challenge = models.JSONField()
    device_hint = models.CharField(max_length=100)
    expires_at = models.DateTimeField()
    consumed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "attendance_checkin_attempt"


class CheckIn(BaseModel):
    class Status(models.TextChoices):
        PRESENT = "PRESENT", "Present"
        FLAGGED = "FLAGGED", "Flagged"
        ABSENT = "ABSENT", "Absent"

    session = models.ForeignKey(ClassSession, on_delete=models.CASCADE)
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.FLAGGED)
    latitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    accuracy_m = models.FloatField(null=True, blank=True)
    distance_m = models.FloatField(null=True, blank=True)
    passkey_credential = models.ForeignKey(
        PasskeyCredential,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="checkins",
    )
    device_hint = models.CharField(max_length=100)
    network_ip = models.GenericIPAddressField(null=True, blank=True)
    flag_reasons = models.JSONField(default=list)
    checked_in_at = models.DateTimeField()
    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_checkins",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_note = models.TextField(blank=True)

    class Meta:
        db_table = "attendance_checkin"
        unique_together = [["session", "student"]]


class SpotCheck(BaseModel):
    class Outcome(models.TextChoices):
        PENDING = "PENDING", "Pending"
        CONFIRMED = "CONFIRMED", "Confirmed"
        NOT_PRESENT = "NOT_PRESENT", "Not Present"

    session = models.ForeignKey(ClassSession, on_delete=models.CASCADE)
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    outcome = models.CharField(max_length=20, choices=Outcome.choices, default=Outcome.PENDING)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "attendance_spot_check"
        unique_together = [["session", "student"]]
