# HTTP audit logging and login events

Configure the root OpenAPI document (or the project's `backend/openapi/base.yaml`):

```yaml
middleware:
  auditlog:
    enabled: true
    before_request: true
    exclude_models:
      - vehicle
```

Both booleans default to `false`. Model exclusions are case-insensitive and apply
to successes and errors. AuditLog requests are excluded to avoid auditing the
audit reader itself. The generated OpenAPI export preserves this configuration.

The middleware records one entry per application HTTP request: CRUD, searches,
aggregations, auth and custom routes, including validation failures, rejected
authorization and unhandled errors. Unmatched routes use model `System`.
Application service calls outside an HTTP request do not create API audit entries.
CRUD services enrich the entry with the before/after snapshots they actually
read/write; other routes can have null snapshots. Failed authorization does not
trigger extra reads of protected records just to obtain a snapshot.

Entries include `action`, `model`, `resource_id`, `user: {id}`, `request`, `changes`,
`result`, `metadata` and `createdAt`. `result.status_code` comes from the HTTP
response rather than from an assumed success in a service. Credentials in JSON,
query/path parameters and snapshots are redacted. Raw binary, multipart, malformed
JSON and JSON bodies above 64 KiB are omitted from the audit payload; the original
body still reaches the application. IP uses the ASGI client address, not an
untrusted forwarded header.

`metadata.request_id` matches the `X-Request-ID` response header. A supplied
`X-Request-ID` is accepted only if it contains 1–128 letters, digits or `_.:-`;
otherwise a UUID is generated. Concurrent requests have separate audit state.

With `before_request: true`, a durable entry with `metadata.phase: started` and a
null result is inserted before the handler executes. That same entry is updated
to `completed` afterwards. The request is rejected with 503 if the initial write
fails, so the business handler does not run. A failure to complete an audit also
returns 503, leaving the started entry for investigation. An interrupted request
may likewise leave a started entry. Business changes and audit completion are not
a shared database transaction: a late audit failure can occur after the business
change, so callers should check the resource before retrying a non-idempotent write.
With `before_request: false`, only the completed entry is written, before the
response starts; late persistence failure still returns 503. Streaming failures
after response headers mark the entry unsuccessful with `response_incomplete`.

## LoginEvent hook

The User schema can configure a required login hook:

```yaml
x-hooks:
  auth_login:
    - script: user/add_login_event
```

The script's `run(context)` receives `element`, `repository`, `services`,
`request` and `request_context` (including IP/user agent). It must persist the
LoginEvent or raise an exception. The framework does not return login tokens
when a configured hook fails or cannot be loaded: it returns 503. Invalid
credentials do not run the hook. This behavior is independent of whether HTTP
audit logging is enabled. The project must include the LoginEvent schema and
the hook file; there is no implicit installation for models without this hook.

## Access policy

AuditLog and LoginEvent HTTP endpoints require an authenticated administrator,
using a valid access JWT with the `admin` role name or its stored role ID.
Only read/search are allowed. HTTP create/update/delete/aggregate are refused,
even for administrators; middleware/hooks write internally through the repository.
This guard remains active when logging is disabled and when a schema was
accidentally declared public. Refresh tokens are not accepted for these reads.
Other models' aggregate endpoints cannot overwrite either collection using
`$out`/`$merge`; non-admins also cannot read them via `$lookup`/`$unionWith`.
Deployments must still restrict direct database access separately.

## Validation

Run with a local MongoDB and the repository's Python requirements installed:

```sh
python -m pytest tests/Integration/test_audit_login.py --confcutdir=tests/Integration
```

`LAIA_TEST_MONGO_URI` overrides the test MongoDB URI. Each test creates a unique
`laia_audit_integration_*` database and removes only that database afterwards.
`LAIA_LOGIN_HOOK_DIR` can point to a consuming application's `backend/hooks` to
exercise its actual login script; otherwise the self-contained test hook is used.
Tests also cover API construction, model generation and OpenAPI configuration
round-tripping. `datamodel-codegen` must be on PATH for the construction test.
