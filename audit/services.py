from __future__ import annotations

from typing import Any

from django.contrib.auth.models import AnonymousUser

from audit.models import AuditLog


def log_action(user, action: str, object_type: str, object_id: object = "", *, request=None, summary: dict[str, Any] | None = None) -> None:
    ip_address = None
    user_agent = ""
    if request is not None:
        ip_address = _client_ip(request)
        user_agent = request.META.get("HTTP_USER_AGENT", "")
    AuditLog.objects.create(
        user=None if isinstance(user, AnonymousUser) else user,
        action=action,
        object_type=object_type,
        object_id=str(object_id or ""),
        ip_address=ip_address,
        user_agent=user_agent,
        summary=summary or {},
    )


def _client_ip(request) -> str | None:
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")

