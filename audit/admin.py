from __future__ import annotations

from django.contrib import admin

from audit.models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("action", "object_type", "object_id", "user", "ip_address", "created_at")
    list_filter = ("action", "object_type", "created_at")
    search_fields = ("action", "object_type", "object_id", "user__username")
    readonly_fields = ("created_at",)

