from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from fastapi import Request

from laiagenlib.Domain.Shared.Utils.SerializeBson import serialize_bson
from laiagenlib.Domain.Shared.Utils.logger import _logger

SENSITIVE_KEYS = {"password", "token", "refresh_token", "resetToken", "reset_token"}


def redact_sensitive(value: Any) -> Any:
    if isinstance(value, dict):
        redacted = {}
        for key, item in value.items():
            if str(key) in SENSITIVE_KEYS:
                redacted[key] = "***"
            else:
                redacted[key] = redact_sensitive(item)
        return redacted
    if isinstance(value, list):
        return [redact_sensitive(item) for item in value]
    return serialize_bson(value)


def build_audit_context(request: Optional[Request] = None, user_id: Any = None, payload: Any = None) -> dict:
    if not request:
        return {
            "method": None,
            "path": None,
            "query": {},
            "params": {},
            "payload": redact_sensitive(payload or {}),
            "ip": None,
            "user_agent": None,
        }

    return {
        "method": request.method,
        "path": str(request.url.path),
        "query": dict(request.query_params),
        "params": dict(request.path_params),
        "payload": redact_sensitive(payload or {}),
        "ip": request.client.host if request.client else None,
        "user_agent": request.headers.get("user-agent"),
    }


async def write_audit_log(
    repository,
    action: str,
    model_name: str,
    resource_id: Any = None,
    user_id: Any = None,
    request_context: Optional[dict] = None,
    before: Any = None,
    after: Any = None,
    status_code: int = 200,
    success: bool = True,
    metadata: Optional[dict] = None,
):
    if not repository or not model_name or request_context is None:
        return

    normalized_model_name = str(model_name).lower()
    if normalized_model_name == "auditlog":
        return

    entry = {
        "action": action,
        "model": model_name,
        "resource_id": str(resource_id) if resource_id is not None else None,
        "userId": str(user_id) if user_id is not None else None,
        "request": request_context,
        "changes": {
            "before": redact_sensitive(before),
            "after": redact_sensitive(after),
        },
        "result": {
            "status_code": status_code,
            "success": success,
        },
        "metadata": {
            "source": "api",
            "request_id": str(uuid4()),
            **(metadata or {}),
        },
        "createdAt": datetime.now(timezone.utc),
    }

    try:
        await repository.post_item("auditlog", entry)
    except Exception as exc:
        _logger.warning("AuditLog could not be written for %s %s: %s", action, model_name, exc)