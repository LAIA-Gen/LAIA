"""Request-local audit enrichment. Persistence is owned by AuditMiddleware."""
from contextvars import ContextVar
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Optional

from fastapi import Request

from laiagenlib.Domain.Shared.Utils.SerializeBson import serialize_bson


SENSITIVE_KEYS = {
    'password', 'token', 'accesstoken', 'refreshtoken', 'resettoken',
    'authorization', 'cookie', 'secret', 'secretkey', 'apikey',
    'oldpassword', 'newpassword', 'confirmpassword',
}


def redact_sensitive(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: '***' if str(key).replace('_', '').replace('-', '').lower() in SENSITIVE_KEYS
            else redact_sensitive(item)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [redact_sensitive(item) for item in value]
    return serialize_bson(value)


@dataclass
class AuditState:
    enabled: bool
    user_id: Optional[str] = None
    action: Optional[str] = None
    model: Optional[str] = None
    resource_id: Optional[str] = None
    before: Any = None
    after: Any = None
    metadata: dict = field(default_factory=dict)


current_audit: ContextVar[Optional[AuditState]] = ContextVar('laia_audit', default=None)


def capture_audit_changes(*, before=None, after=None):
    state = current_audit.get()
    if state is not None and state.enabled:
        if before is not None:
            state.before = redact_sensitive(deepcopy(before))
        if after is not None:
            state.after = redact_sensitive(deepcopy(after))


def build_audit_context(request: Optional[Request] = None, user_id: Any = None, payload: Any = None) -> dict:
    state = current_audit.get()
    if state is not None and user_id is not None:
        state.user_id = str(user_id)
    return {
        'method': request.method if request else None,
        'path': str(request.url.path) if request else None,
        'query': redact_sensitive(dict(request.query_params)) if request else {},
        'params': redact_sensitive(dict(request.path_params)) if request else {},
        'payload': redact_sensitive(payload if payload is not None else {}),
        'ip': request.client.host if request and request.client else None,
        'user_agent': request.headers.get('user-agent') if request else None,
    }


async def write_audit_log(
    repository, action: str, model_name: str, resource_id: Any = None,
    user_id: Any = None, request_context: Optional[dict] = None,
    before: Any = None, after: Any = None, status_code: int = 200,
    success: bool = True, metadata: Optional[dict] = None,
):
    """Enrich the one audit entry for this request; never bypass configuration.

    The middleware uses the actual HTTP status, including validation/auth failures.
    Calls outside an HTTP audit scope do not create misleading API audit records.
    """
    state = current_audit.get()
    if state is None or not state.enabled or request_context is None:
        return
    state.action = action
    state.model = model_name
    if resource_id is not None:
        state.resource_id = str(resource_id)
    if user_id is not None:
        state.user_id = str(user_id)
    capture_audit_changes(before=before if state.before is None else None,
                          after=after if state.after is None else None)
    state.metadata.update(metadata or {})
