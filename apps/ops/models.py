from django.db import models

from apps.core.models import BaseModel


class JobRunStatus(models.TextChoices):
    RUNNING = "RUNNING", "Running"
    SUCCEEDED = "SUCCEEDED", "Succeeded"
    FAILED = "FAILED", "Failed"


class JobRun(BaseModel):
    name = models.CharField(max_length=100)
    status = models.CharField(max_length=20, choices=JobRunStatus.choices, default=JobRunStatus.RUNNING)
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    lease_expires_at = models.DateTimeField()
    stats = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "ops_job_run"
        constraints = [
            models.UniqueConstraint(
                fields=["name"],
                condition=models.Q(status=JobRunStatus.RUNNING),
                name="unique_running_job_per_name",
            )
        ]
        indexes = [
            models.Index(fields=["name", "-started_at"]),
            models.Index(fields=["status"]),
        ]
