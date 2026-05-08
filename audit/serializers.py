from __future__ import annotations

from rest_framework import serializers

from audit.models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = AuditLog
        fields = ["id", "username", "action", "object_type", "object_id", "ip_address", "user_agent", "summary", "created_at"]

