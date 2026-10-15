import csv
import io
from datetime import timedelta

from django.db import transaction

from apps.accounts.domain.password import generate_activation_code, hash_code
from apps.accounts.models import ActivationCode, User
from apps.audit.services.record import record
from apps.core.clock import Clock


@transaction.atomic
def import_users_from_csv(
    csv_data: str,
    actor: User,
    clock: Clock,
) -> dict:
    """Import users from CSV. Format: student_number, full_name, email, course_codes
    Returns: {"created": int, "updated": int, "errors": list[str]}
    """
    reader = csv.DictReader(io.StringIO(csv_data))
    created = 0
    updated = 0
    errors = []

    for row_num, row in enumerate(reader, start=2):
        try:
            student_number = row["student_number"].strip()
            full_name = row["full_name"].strip()
            email = row["email"].strip()
            row.get("course_codes", "").strip()

            if not all([student_number, full_name, email]):
                errors.append(f"Row {row_num}: Missing required fields")
                continue

            user, created_user = User.objects.update_or_create(
                student_number=student_number,
                defaults={
                    "email": email,
                    "full_name": full_name,
                    "role": User.Role.STUDENT,
                    "is_active": False,
                },
            )

            if created_user:
                code = generate_activation_code()
                ActivationCode.objects.create(
                    user=user,
                    purpose=ActivationCode.Purpose.ACTIVATION,
                    code_hash=hash_code(code),
                    expires_at=clock.now() + timedelta(days=7),
                )
                created += 1
            else:
                updated += 1

        except Exception as e:
            errors.append(f"Row {row_num}: {str(e)}")

    record(
        actor=actor,
        action="USERS_IMPORTED",
        target_type="User",
        target_id="bulk",
        metadata={"created": created, "updated": updated, "errors_count": len(errors)},
    )

    return {"created": created, "updated": updated, "errors": errors}
