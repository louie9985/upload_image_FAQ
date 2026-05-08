from __future__ import annotations

from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="用户", null=True, blank=True, on_delete=models.SET_NULL)
    action = models.CharField("操作", max_length=64)
    object_type = models.CharField("对象类型", max_length=64)
    object_id = models.CharField("对象 ID", max_length=64, blank=True)
    ip_address = models.GenericIPAddressField("IP 地址", null=True, blank=True)
    user_agent = models.TextField("User-Agent", blank=True)
    summary = models.JSONField("摘要", default=dict, blank=True)
    created_at = models.DateTimeField("创建时间", auto_now_add=True)

    class Meta:
        verbose_name = "操作日志"
        verbose_name_plural = "操作日志"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.action} {self.object_type} {self.object_id}"

