from __future__ import annotations

from rest_framework import viewsets
from rest_framework.permissions import IsAdminUser

from audit.models import AuditLog
from audit.serializers import AuditLogSerializer


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AuditLogSerializer
    permission_classes = [IsAdminUser]
    queryset = AuditLog.objects.select_related("user").all()

