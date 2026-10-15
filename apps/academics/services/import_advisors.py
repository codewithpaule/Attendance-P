import csv
import io

from django.db import transaction

from apps.academics.models import AdvisorAssignment
from apps.accounts.models import User
from apps.audit.services.record import record
from apps.core.clock import Clock


@transaction.atomic
def import_advisor_assignments_from_csv(
    csv_data: str,
    actor: User,
    clock: Clock,
) -> dict:
    """Import advisor assignments from CSV. Format: advisor_email, student_number
    Returns: {"created": int, "updated": int, "errors": list[str]}
    """
    reader = csv.DictReader(io.StringIO(csv_data))
    created = 0
    updated = 0
    errors = []

    for row_num, row in enumerate(reader, start=2):
        try:
            advisor_email = row["advisor_email"].strip()
            student_number = row["student_number"].strip()

            if not all([advisor_email, student_number]):
                errors.append(f"Row {row_num}: Missing required fields")
                continue

            advisor = User.objects.filter(
                email=advisor_email, role=User.Role.ADVISOR
            ).first()
            if not advisor:
                errors.append(f"Row {row_num}: Advisor not found: {advisor_email}")
                continue

            student = User.objects.filter(
                student_number=student_number, role=User.Role.STUDENT
            ).first()
            if not student:
                errors.append(f"Row {row_num}: Student not found: {student_number}")
                continue

            assignment, created_assignment = AdvisorAssignment.objects.get_or_create(
                advisor=advisor, student=student
            )

            if created_assignment:
                created += 1
            else:
                updated += 1

        except Exception as e:
            errors.append(f"Row {row_num}: {str(e)}")

    record(
        actor=actor,
        action="ADVISOR_ASSIGNMENTS_IMPORTED",
        target_type="AdvisorAssignment",
        target_id="bulk",
        metadata={"created": created, "updated": updated, "errors_count": len(errors)},
    )

    return {"created": created, "updated": updated, "errors": errors}
