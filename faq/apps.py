from __future__ import annotations

from django.apps import AppConfig


class FaqConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "faq"
    verbose_name = "问答任务"

