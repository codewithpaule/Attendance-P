import csv
import io

from django.db import transaction

from apps.academics.models import Course, Enrollment
from apps.accounts.models import User
from apps.audit.services.record import record
from apps.core.clock import Clock


@transaction.atomic
def import_enrollments_from_csv(
    csv_data: str,
    actor: User,
    clock: Clock,
) -> dict:
    """Import enrollments from CSV. Format: student_number, course_code
    Returns: {"created": int, "updated": int, "errors": list[str]}
    """
    reader = csv.DictReader(io.StringIO(csv_data))
    created = 0
    updated = 0
    errors = []

    for row_num, row in enumerate(reader, start=2):
        try:
            student_number = row["student_number"].strip()
            course_code = row["course_code"].strip()

            if not all([student_number, course_code]):
                errors.append(f"Row {row_num}: Missing required fields")
                continue

            student = User.objects.filter(
                student_number=student_number, role=User.Role.STUDENT
            ).first()
            if not student:
                errors.append(f"Row {row_num}: Student not found: {student_number}")
                continue

            course = Course.objects.filter(code=course_code).first()
            if not course:
                errors.append(f"Row {row_num}: Course not found: {course_code}")
                continue

            enrollment, created_enrollment = Enrollment.objects.get_or_create(
                student=student, course=course
            )

            if created_enrollment:
                created += 1
            else:
                updated += 1

        except Exception as e:
            errors.append(f"Row {row_num}: {str(e)}")

    record(
        actor=actor,
        action="ENROLLMENTS_IMPORTED",
        target_type="Enrollment",
        target_id="bulk",
        metadata={"created": created, "updated": updated, "errors_count": len(errors)},
    )

    return {"created": created, "updated": updated, "errors": errors}
