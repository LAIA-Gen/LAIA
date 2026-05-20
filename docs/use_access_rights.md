# Access Rights in LAIA

Access-right enforcement is currently **built into CRUD operations by default for non-admin users** via the `AccessRight` model and related controllers/services.

## How access rights work

### 1. Data model
Access rights are stored in the `accessright` collection/table (`AccessRight` model) with:

- `role`: role id (relation to `Role`)
- `model`: target model name in lowercase
- `operations`: dict with allowed operations (`create`, `read`, `update`, `delete`, `search`) as integers (typically `0` or `1`)
- `fields_create`: per-field create permission map
- `fields_edit`: per-field update permission map
- `fields_visible`: per-field visibility map
- `owner`: boolean flag used by search to force own-record filtering

## 2. Runtime enforcement path
For non-admin users (`"admin"` not in `user_roles`):

- Operation-level check: `check_access_rights_of_user(...)`
- Field-level check (create/update): `check_access_rights_of_fields(...)`
- Output field filtering (create/read/update/search response): `get_allowed_fields(...)` using `fields_visible`

For admin users:

- Access checks are bypassed in standard model CRUD handlers.

## 3. Per-operation behavior

- `create`: requires `operations.create >= 1`; each submitted field must be allowed in `fields_create`.
- `read`: requires `operations.read >= 1`; returned payload is filtered by `fields_visible` (+ always `id`).
- `update`: requires `operations.update >= 1`; updated fields must be allowed in `fields_edit`; response filtered by `fields_visible`.
- `delete`: requires `operations.delete >= 1`.
- `search`: requires `operations.search >= 1`; response items filtered by `fields_visible`.

### Owner-restricted search
In search, if **all matching rights have `owner = true`**, LAIA injects `filters["owner"] = <current_user_id>`.

If at least one matching right has `owner = false`, no owner filter is forced.

## 4. API routes for access-right management
Routes are auto-created by `create_access_rights_routes(...)`:

- `POST /accessright/` create AccessRight
- `PUT /accessright/{element_id}` update AccessRight
- `GET /accessright/{element_id}` read AccessRight
- `DELETE /accessright/{element_id}` delete AccessRight
- `POST /accessrights/` search AccessRights

### Who can manage AccessRights
- Create/update AccessRight is restricted to users with admin role.
- Create also validates:
  - role exists
  - model name matches target model
  - operations format and field maps are valid
  - uniqueness by `(model, role)`
- Update does **not** allow changing `model` or `role`.

## 5. Setup: how to configure access rights

1. Ensure roles exist (`/role/` endpoints). An `admin` role is auto-created if missing.
2. Create users and assign role ids in their `roles` list.
3. Create one `AccessRight` per `(role, model)`.
4. Fill:
   - `operations`: set allowed operations to `1`, denied to `0`
   - `fields_create`, `fields_edit`, `fields_visible`: per-field `1`/`0`
   - `owner`: `true` for own-record-only search, `false` otherwise

## 6. Example AccessRight payload

```json
{
  "name": "drone_user_rights",
  "role": "<role_id_user>",
  "model": "drone",
  "operations": {
    "create": 1,
    "read": 1,
    "update": 0,
    "delete": 0,
    "search": 1
  },
  "fields_create": {
    "name": 1,
    "description": 1,
    "weight": 0,
    "max_altitude": 0,
    "max_speed": 0
  },
  "fields_edit": {
    "description": 1
  },
  "fields_visible": {
    "name": 1,
    "description": 1
  },
  "owner": true
}
```

## 7. Practical consequences
- Access control is **allow-list based**.
- If a non-admin user has multiple roles, rights are effectively merged permissively:
  - operation allowed if at least one role grants it
  - a field is allowed if at least one role grants it
- If no AccessRight grants an operation, request fails with `PermissionError`.

## 8. Current limitations to know
- There is no central on/off switch named `use_access_rights` in current code.
- `read` does not enforce ownership (only `search` has owner-based filtering).
- `fields_visible` controls output shape; non-visible fields are dropped from responses for non-admin users.
