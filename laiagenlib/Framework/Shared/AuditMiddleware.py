"""One audit entry per HTTP request, including rejected and failed requests."""
import json
import re
from datetime import datetime, timezone
from uuid import uuid4

from bson import ObjectId
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Match

from ...Application.Audit.AuditLogger import AuditState, current_audit, redact_sensitive
from ...Application.LaiaUser.JWTToken import verify_jwt_token
from ...Domain.Shared.Utils.logger import _logger


class AuditPersistenceError(Exception):
    pass


def route_details(api, scope):
    selected = None
    for route in api.routes:
        match, child = route.matches(scope)
        if match == Match.FULL:
            selected = (route, child)
            break
        if match == Match.PARTIAL and selected is None:
            selected = (route, child)
    if selected:
        route, child = selected
        tags = getattr(route, 'tags', [])
        model = str(tags[0]) if tags else 'System'
        name = getattr(route, 'name', '').lower()
        action = {'GET': 'READ', 'HEAD': 'READ', 'POST': 'CREATE',
                  'PUT': 'UPDATE', 'PATCH': 'UPDATE', 'DELETE': 'DELETE'}.get(scope['method'], 'REQUEST')
        if 'aggregate' in name:
            action = 'AGGREGATE'
        elif 'search' in name:
            action = 'SEARCH'
        if '/auth/' in scope['path']:
            action = scope['path'].split('/auth/', 1)[1].split('/')[0].upper()
        params = child.get('path_params', {})
        resource = next((str(v) for k, v in params.items() if k == 'id' or k.endswith('_id')), None)
        return model, action, params, resource
    return 'System', 'REQUEST', {}, None


class AuditMiddleware:
    def __init__(self, app, *, api, repository, config, jwt_secret):
        self.app = app
        self.api = api
        self.repository = repository
        self.config = config
        self.jwt_secret = jwt_secret

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            await self.app(scope, receive, send)
            return
        model, action, params, resource = route_details(self.api, scope)
        request = Request(scope)
        request_id = request.headers.get('x-request-id', '')
        if not re.fullmatch(r'[A-Za-z0-9_.:-]{1,128}', request_id):
            request_id = str(uuid4())
        claims = None
        authorization = request.headers.get('authorization', '')
        if authorization.lower().startswith('bearer '):
            try:
                claims = verify_jwt_token(authorization[7:], self.jwt_secret)
                if claims.get('type', 'access') != 'access':
                    claims = None
            except ValueError:
                pass

        enabled = self.config.enabled and model.casefold() not in self.config.exclude_models and model.casefold() != 'auditlog'
        state = AuditState(enabled, user_id=str(claims['user_id']) if claims and claims.get('user_id') else None,
                           action=action, model=model, resource_id=resource)
        context_token = current_audit.set(state)
        audit_id = None
        created_at = datetime.now(timezone.utc)
        captured = bytearray()
        truncated = False
        response_started = False
        response_status = None
        safe_params = redact_sensitive(params)
        safe_path = scope['path']
        for key, value in params.items():
            if safe_params.get(key) == '***':
                safe_path = safe_path.replace(str(value), '***')

        async def capture_receive():
            nonlocal truncated
            message = await receive()
            if message['type'] == 'http.request' and state.enabled:
                body = message.get('body', b'')
                remaining = 65536 - len(captured)
                captured.extend(body[:remaining])
                truncated = truncated or len(body) > remaining
            return message

        def entry(status_code, phase):
            payload = {}
            if truncated:
                payload = {'_omitted': 'Request body exceeds audit limit'}
            elif captured:
                try:
                    payload = redact_sensitive(json.loads(captured))
                except (ValueError, UnicodeError):
                    # Do not persist raw multipart/binary or malformed bodies:
                    # they may contain credentials that cannot be safely redacted.
                    payload = {'_omitted': 'Non-JSON request body'}
            return {
                'action': state.action, 'model': state.model, 'resource_id': state.resource_id,
                'user': {'id': state.user_id},
                'request': {'method': scope['method'], 'path': safe_path,
                            'query': redact_sensitive(dict(request.query_params)), 'params': safe_params,
                            'payload': payload, 'ip': request.client.host if request.client else None,
                            'user_agent': request.headers.get('user-agent')},
                'changes': {'before': state.before, 'after': state.after},
                'result': {'status_code': status_code, 'success': (status_code < 400 and not state.metadata.get('response_incomplete', False)) if status_code is not None else None},
                'metadata': {**redact_sensitive(state.metadata), 'source': 'api', 'request_id': request_id, 'phase': phase},
                'createdAt': created_at,
            }

        async def persist(status_code, phase):
            nonlocal audit_id
            if not state.enabled:
                return
            try:
                document = entry(status_code, phase)
                if audit_id is None:
                    saved = await self.repository.post_item('auditlog', document)
                    audit_id = saved['id']
                else:
                    await self.repository.put_item('auditlog', audit_id, document)
            except Exception as exc:
                raise AuditPersistenceError('Audit storage unavailable') from exc

        async def audit_send(message):
            nonlocal response_started, response_status
            if message['type'] == 'http.response.start':
                await persist(message['status'], 'completed')
                message = dict(message)
                message['headers'] = [(k, v) for k, v in message.get('headers', []) if k.lower() != b'x-request-id']
                message['headers'].append((b'x-request-id', request_id.encode()))
                response_started = True
                response_status = message['status']
            await send(message)

        try:
            if state.enabled and self.config.before_request:
                await persist(None, 'started')
            if model.casefold() in {'auditlog', 'loginevent'}:
                status_code = await self.protected_status(claims, action)
                if status_code:
                    await JSONResponse({'detail': 'Audit records are read-only and restricted to administrators'},
                                       status_code=status_code)(scope, capture_receive, audit_send)
                    return
            await self.app(scope, capture_receive, audit_send)
        except AuditPersistenceError:
            if response_started:
                raise
            await JSONResponse({'detail': 'Audit storage unavailable'}, status_code=503,
                               headers={'X-Request-ID': request_id})(scope, receive, send)
        except Exception:
            if response_started:
                state.metadata['response_incomplete'] = True
            try:
                await persist(response_status if response_started else 500, 'completed')
            except AuditPersistenceError:
                pass  # Preserve the original server error; started entries remain durable.
            if response_started:
                raise
            _logger.exception('Unhandled request failure')
            await JSONResponse({'detail': 'Internal Server Error'}, status_code=500,
                               headers={'X-Request-ID': request_id})(scope, receive, send)
        finally:
            current_audit.reset(context_token)

    async def protected_status(self, claims, action):
        if not claims:
            return 401
        roles = claims.get('user_roles') or []
        if not isinstance(roles, list):
            roles = []
        is_admin = 'admin' in roles
        for role in roles:
            if not is_admin and ObjectId.is_valid(role):
                try:
                    found = await self.repository.get_item('role', str(role))
                    is_admin = found.get('name') == 'admin'
                except ValueError:
                    pass
        if not is_admin:
            return 403
        # Aggregation is deliberately not a read-only API: $out/$merge can write.
        if action not in {'READ', 'SEARCH'}:
            return 405
        return None
