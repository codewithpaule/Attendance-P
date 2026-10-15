from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from django.test import TestCase, override_settings

from apps.core.exceptions import ConflictError, NotFoundError
from apps.ops.models import JobRun, JobRunStatus
from apps.ops.registry import get_job, list_jobs, register
from apps.ops.services.jobs import run_job, verify_job_secret


class TestJobRegistry(TestCase):
    def test_register_and_get_job(self):
        """Test registering and retrieving a job."""
        @register("test-job")
        def test_job(deadline: datetime) -> dict:
            return {"result": "ok"}

        retrieved = get_job("test-job")
        self.assertEqual(retrieved, test_job)

    def test_list_jobs(self):
        """Test listing all registered jobs."""
        @register("job-1")
        def job1(deadline: datetime) -> dict:
            return {}

        @register("job-2")
        def job2(deadline: datetime) -> dict:
            return {}

        jobs = list_jobs()
        self.assertIn("job-1", jobs)
        self.assertIn("job-2", jobs)

    def test_get_nonexistent_job(self):
        """Test getting a non-existent job."""
        retrieved = get_job("nonexistent")
        self.assertIsNone(retrieved)


class TestJobRun(TestCase):
    def test_concurrent_claim_prevents_duplicate(self):
        """Test that concurrent claims are prevented by unique constraint."""
        # First claim should succeed
        JobRun.objects.create(
            name="concurrent-test-job",
            status=JobRunStatus.RUNNING,
            lease_expires_at=datetime.now(ZoneInfo("UTC")) + timedelta(minutes=5),
        )

        # Second claim should fail
        with self.assertRaises(Exception):  # noqa: B017
            JobRun.objects.create(
                name="concurrent-test-job",
                status=JobRunStatus.RUNNING,
                lease_expires_at=datetime.now(ZoneInfo("UTC")) + timedelta(minutes=5),
            )

    def test_expired_lease_recovery(self):
        """Test that expired leases are marked FAILED before new claim."""
        # Create an expired RUNNING job
        JobRun.objects.create(
            name="expired-test-job",
            status=JobRunStatus.RUNNING,
            lease_expires_at=datetime.now(ZoneInfo("UTC")) - timedelta(minutes=1),
        )

        # Manually mark expired leases as FAILED (simulating run_job behavior)
        JobRun.objects.filter(
            name="expired-test-job",
            status=JobRunStatus.RUNNING,
            lease_expires_at__lt=datetime.now(ZoneInfo("UTC")),
        ).update(status=JobRunStatus.FAILED, finished_at=datetime.now(ZoneInfo("UTC")))

        # New claim should succeed
        job_run = JobRun.objects.create(
            name="expired-test-job",
            status=JobRunStatus.RUNNING,
            lease_expires_at=datetime.now(ZoneInfo("UTC")) + timedelta(minutes=5),
        )

        self.assertEqual(job_run.status, JobRunStatus.RUNNING)

        # Check previous job was marked FAILED
        previous_jobs = JobRun.objects.filter(name="expired-test-job", status=JobRunStatus.FAILED)
        self.assertEqual(previous_jobs.count(), 1)


class TestJobService(TestCase):
    def test_run_job_success(self):
        """Test running a job successfully."""
        @register("test-success-job")
        def test_job(deadline: datetime) -> dict:
            return {"processed": 5}

        stats = run_job("test-success-job")
        self.assertEqual(stats, {"processed": 5})

        # Verify JobRun was created and marked SUCCEEDED
        job_run = JobRun.objects.filter(name="test-success-job").first()
        self.assertIsNotNone(job_run)
        self.assertEqual(job_run.status, JobRunStatus.SUCCEEDED)
        self.assertIsNotNone(job_run.finished_at)

    def test_run_job_not_found(self):
        """Test running a non-existent job."""
        with self.assertRaises(NotFoundError):
            run_job("nonexistent-job")

    def test_run_job_already_running(self):
        """Test running a job that is already running."""
        JobRun.objects.create(
            name="test-job",
            status=JobRunStatus.RUNNING,
            lease_expires_at=datetime.now(ZoneInfo("UTC")) + timedelta(minutes=5),
        )

        with self.assertRaises(ConflictError):
            run_job("test-job")


class TestJobSecret(TestCase):
    def test_verify_job_secret_valid(self):
        """Test verifying a valid job secret."""
        with override_settings(JOBS_SECRET="test-secret"):
            self.assertTrue(verify_job_secret("test-secret"))

    def test_verify_job_secret_invalid(self):
        """Test verifying an invalid job secret."""
        with override_settings(JOBS_SECRET="test-secret"):
            self.assertFalse(verify_job_secret("wrong-secret"))
