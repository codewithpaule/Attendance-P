import logging

from django.db import transaction

from apps.accounts.models import User
from apps.audit.models import AuditLog

logger = logging.getLogger(__name__)


@transaction.atomic
def record(
    actor: User | None,
    action: str,
    target_type: str,
    target_id: str,
    metadata: dict | None = None,
    ip: str | None = None,
) -> AuditLog:
    audit_entry = AuditLog.objects.create(
        actor=actor,
        action=action,
        target_type=target_type,
        target_id=target_id,
        metadata=metadata or {},
        ip=ip,
    )
    logger.info(
        f"Audit log: {action} on {target_type}:{target_id} by {actor.email if actor else 'system'}",
        extra={
            "action": action,
            "target_type": target_type,
            "target_id": target_id,
            "actor": actor.email if actor else "system",
        },
    )
    return audit_entry
