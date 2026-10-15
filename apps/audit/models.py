from django.db import models

from apps.accounts.models import User
from apps.core.models import BaseModel


class AuditLog(BaseModel):
    actor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=100)
    target_type = models.CharField(max_length=100)
    target_id = models.CharField(max_length=255)
    metadata = models.JSONField(default=dict)
    ip = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        db_table = "audit_log"
