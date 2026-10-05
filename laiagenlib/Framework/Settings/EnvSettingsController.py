import os
import bcrypt
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Header, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from bson import ObjectId
from pydantic import BaseModel

security_scheme = HTTPBearer(auto_error=False)


class UpdateEnvRequest(BaseModel):
    variables: Dict[str, str]

def _read_env_file(path: str) -> Dict[str, str]:
    env_vars = {}
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    env_vars[k.strip()] = v.strip().strip("'\"")
    return env_vars

def _write_env_file(path: str, new_vars: Dict[str, str]):
    existing_lines = []
    keys_written = set()

    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            existing_lines = f.readlines()

    updated_lines = []
    for line in existing_lines:
        trimmed = line.strip()
        if trimmed and not trimmed.startswith("#") and "=" in trimmed:
            k = trimmed.split("=", 1)[0].strip()
            if k in new_vars:
                updated_lines.append(f"{k}={new_vars[k]}\n")
                keys_written.add(k)
        else:
            updated_lines.append(line)

    for k, v in new_vars.items():
        if k not in keys_written:
            updated_lines.append(f"{k}={v}\n")

    with open(path, "w", encoding="utf-8") as f:
        f.writelines(updated_lines)

def EnvSettingsController(
    db,
    jwt_secret_key: str,
    user_collection: str = "user",
    env_file_path: Optional[str] = None,
    custom_keys: Optional[List[str]] = None,
) -> APIRouter:
    router = APIRouter(prefix="/admin/settings", tags=["Admin Settings"])
    active_env_file = env_file_path or os.path.join(os.getcwd(), ".env")

    def _verify_admin_sudo(
        credentials: Optional[HTTPAuthorizationCredentials] = Security(security_scheme),
        x_admin_password: Optional[str] = Header(None, alias="X-Admin-Password"),
    ) -> dict:
        if not credentials or not credentials.credentials:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication token required",
            )

        if not x_admin_password:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Administrator password is required for security verification",
            )

        token = credentials.credentials
        try:
            payload = jwt.decode(token, jwt_secret_key, algorithms=["HS256"])
        except jwt.PyJWTError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid authentication token: {str(e)}",
            )

        user_id = payload.get("user_id") or payload.get("sub") or payload.get("id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token invalid: missing user identifier",
            )

        user_id_str = str(user_id)
        is_admin = False

        user_name = str(payload.get("user_name", "")).lower()
        if user_name == "admin":
            is_admin = True

        if not is_admin:
            name = str(payload.get("name", "")).lower()
            if name == "admin":
                is_admin = True

        if not is_admin:
            role = str(payload.get("role", "")).lower()
            if role == "admin":
                is_admin = True

        if not is_admin:
            for r_field in ["roles", "user_roles"]:
                val = payload.get(r_field, [])
                if isinstance(val, list) and any(str(r).lower() == "admin" for r in val):
                    is_admin = True
                    break

        user_doc = None
        if db is not None:
            query = (
                {"_id": ObjectId(user_id_str)}
                if ObjectId.is_valid(user_id_str)
                else {"_id": user_id_str}
            )
            colls_to_try = [user_collection]
            if "user" not in colls_to_try:
                colls_to_try.append("user")

            for c in colls_to_try:
                if c in db.list_collection_names():
                    user_doc = db[c].find_one(query) or db[c].find_one({"id": user_id_str})
                    if user_doc:
                        break

            if user_doc and not is_admin:
                doc_name = str(user_doc.get("user_name", "") or user_doc.get("name", "") or user_doc.get("email", "")).lower()
                if doc_name == "admin":
                    is_admin = True
                doc_roles = user_doc.get("roles", []) or [user_doc.get("role")]
                if isinstance(doc_roles, list) and any(str(r).lower() == "admin" for r in doc_roles):
                    is_admin = True

        if not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Administrator privileges required",
            )

        if not user_doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User account not found in database",
            )

        stored_pw = user_doc.get("password")
        if not stored_pw:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User has no password set in database",
            )

        if isinstance(stored_pw, str):
            stored_pw = stored_pw.encode("utf-8")

        if not bcrypt.checkpw(x_admin_password.encode("utf-8"), stored_pw):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid administrator password",
            )

        return user_doc

    @router.get("/env")
    async def get_env_settings(
        credentials: Optional[HTTPAuthorizationCredentials] = Security(security_scheme),
        x_admin_password: Optional[str] = Header(None, alias="X-Admin-Password"),
    ):
        _verify_admin_sudo(credentials, x_admin_password)

        file_vars = _read_env_file(active_env_file)
        all_keys = list(file_vars.keys())

        if custom_keys:
            for ck in custom_keys:
                if ck not in all_keys:
                    all_keys.append(ck)

        variables = []
        for k in all_keys:
            val = file_vars.get(k, os.getenv(k, ""))
            is_secret = any(term in k.upper() for term in ["KEY", "SECRET", "PASSWORD", "TOKEN", "PWD"])
            variables.append({
                "key": k,
                "value": str(val),
                "is_secret": is_secret,
            })

        return {
            "variables": variables,
        }

    @router.put("/env")
    async def update_env_settings(
        body: UpdateEnvRequest,
        credentials: Optional[HTTPAuthorizationCredentials] = Security(security_scheme),
        x_admin_password: Optional[str] = Header(None, alias="X-Admin-Password"),
    ):
        _verify_admin_sudo(credentials, x_admin_password)

        restart_keys = {"BACKEND_PORT", "MONGO_CLIENT_URL", "MONGO_DATABASE_NAME"}
        requires_restart = False

        old_file_vars = _read_env_file(active_env_file)
        for k, v in body.variables.items():
            if k in restart_keys and os.getenv(k) != str(v):
                requires_restart = True
            os.environ[k] = str(v)

        for old_k in old_file_vars.keys():
            if old_k not in body.variables:
                os.environ.pop(old_k, None)

        _write_env_file(active_env_file, body.variables)

        return {
            "success": True,
            "requires_restart": requires_restart,
            "message": "Environment variables updated successfully",
        }

    return router
