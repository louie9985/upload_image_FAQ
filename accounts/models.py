from __future__ import annotations

from django.conf import settings
from django.db import models


class EmployeeProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, verbose_name="系统用户", on_delete=models.CASCADE, related_name="employee_profile")
    external_user_id = models.CharField("外部用户 ID", max_length=128, unique=True)
    name = models.CharField("姓名", max_length=128, blank=True)
    avatar_url = models.URLField("头像链接", blank=True)
    department = models.CharField("部门", max_length=255, blank=True)
    raw_profile = models.JSONField("原始资料", default=dict, blank=True)
    created_at = models.DateTimeField("创建时间", auto_now_add=True)
    updated_at = models.DateTimeField("更新时间", auto_now=True)

    class Meta:
        verbose_name = "员工档案"
        verbose_name_plural = "员工档案"

    def __str__(self) -> str:
        return self.name or self.external_user_id

