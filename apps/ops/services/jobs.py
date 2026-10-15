import hmac
from datetime import timedelta

from django.conf import settings
from django.db import transaction

from apps.audit.services.record import record
from apps.core.clock import DefaultClock
from apps.core.exceptions import ConflictError, NotFoundError
from apps.ops.models import JobRun, JobRunStatus
from apps.ops.registry import get_job


class JobLeaseExpiredError(Exception):
    """Raised when a job lease has expired."""


@transaction.atomic
def run_job(name: str) -> dict:
    """Run a job with lease management.

    Args:
        name: The job name

    Returns:
        Job statistics

    Raises:
        NotFoundError: If job is not registered
        ConflictError: If job is already running
    """
    job_fn = get_job(name)
    if not job_fn:
        raise NotFoundError("JOB_NOT_FOUND", f"Job '{name}' is not registered")

    # Mark expired leases as failed
    clock = DefaultClock()
    JobRun.objects.filter(
        name=name,
        status=JobRunStatus.RUNNING,
        lease_expires_at__lt=clock.now(),
    ).update(status=JobRunStatus.FAILED, finished_at=clock.now())

    # Try to claim the lease
    try:
        job_run = JobRun.objects.create(
            name=name,
            status=JobRunStatus.RUNNING,
            lease_expires_at=clock.now() + timedelta(seconds=settings.JOB_TIME_BUDGET_SECONDS),
        )
    except Exception as err:
        # Unique constraint violation - job already running
        raise ConflictError("JOB_ALREADY_RUNNING", f"Job '{name}' is already running") from err

    # Record job start
    record(
        actor=None,
        action="JOB_STARTED",
        target_type="JobRun",
        target_id=str(job_run.id),
        metadata={"job_name": name},
    )

    # Run the job
    try:
        deadline = job_run.lease_expires_at
        stats = job_fn(deadline)

        # Mark as succeeded
        job_run.status = JobRunStatus.SUCCEEDED
        job_run.finished_at = clock.now()
        job_run.stats = stats
        job_run.save()

        record(
            actor=None,
            action="JOB_SUCCEEDED",
            target_type="JobRun",
            target_id=str(job_run.id),
            metadata={"job_name": name, "stats": stats},
        )

        return stats
    except JobLeaseExpiredError:
        # Mark as failed due to lease expiry
        job_run.status = JobRunStatus.FAILED
        job_run.finished_at = clock.now()
        job_run.stats = {"error": "Lease expired"}
        job_run.save()

        record(
            actor=None,
            action="JOB_FAILED",
            target_type="JobRun",
            target_id=str(job_run.id),
            metadata={"job_name": name, "error": "Lease expired"},
        )

        raise
    except Exception as err:
        # Mark as failed due to error
        job_run.status = JobRunStatus.FAILED
        job_run.finished_at = clock.now()
        job_run.stats = {"error": str(err)}
        job_run.save()

        record(
            actor=None,
            action="JOB_FAILED",
            target_type="JobRun",
            target_id=str(job_run.id),
            metadata={"job_name": name, "error": str(err)},
        )

        raise


def verify_job_secret(secret: str) -> bool:
    """Verify the job secret using constant-time comparison.

    Args:
        secret: The secret to verify

    Returns:
        True if valid, False otherwise
    """
    expected = settings.JOBS_SECRET
    return hmac.compare_digest(secret, expected)
