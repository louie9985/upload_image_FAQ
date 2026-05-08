from __future__ import annotations

from django.contrib import admin

from accounts.models import EmployeeProfile


@admin.register(EmployeeProfile)
class EmployeeProfileAdmin(admin.ModelAdmin):
    list_display = ("external_user_id", "name", "department", "user", "updated_at")
    search_fields = ("external_user_id", "name", "department", "user__username")
    readonly_fields = ("created_at", "updated_at")

