import os
import json
from asyncinit import asyncinit
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from ...Application.Shared.Utils.CreateModelsFile import create_models_file
from ...Application.Shared.Utils.CreateRoutesFile import create_routes_file
from ...Application.Openapi.CreateRoutes import create_crud_routes
from ...Application.LaiaUser.JWTToken import verify_jwt_token
from ...Domain.LaiaBaseModel.ModelRepository import ModelRepository
from ...Domain.Openapi.Openapi import OpenAPI
from ...Domain.Openapi.OpenapiRepository import OpenapiRepository
from ...Domain.Shared.Utils.logger import _logger

@asyncinit
class LaiaFastApi():

    async def __init__(self, openapi, backend_folder_name, db, repository: ModelRepository, repositoryAPI: OpenapiRepository, *args, **kwargs):
        config = self._parse_constructor_config(args, kwargs)
        self.db = db
        self.openapi_path = openapi
        self.openapi = OpenAPI(openapi)
        self.version = config["version"] or self._read_laia_version(self.openapi_path)
        self.api = FastAPI(openapi_url='/openapi.json', version=self.version)
        self.repository_instance = repository(db)
        self.repository_api_instance = repositoryAPI(self.api, config["jwtSecretKey"])
        self.use_ontology = config["use_ontology"]
        self.use_access_rights = config["use_access_rights"]
        self.jwtSecretKey = config["jwtSecretKey"]
        self.jwtRefreshSecretKey = config["jwtRefreshSecretKey"]
        self.storage = config["storage"]
        self.minio_endpoint_url = config["minio_endpoint_url"]
        self.minio_root_user = config["minio_root_user"]
        self.minio_root_password = config["minio_root_password"]
        self.smtp_host = config["smtp_host"]
        self.smtp_port = config["smtp_port"]
        self.smtp_user = config["smtp_user"]
        self.smtp_password = config["smtp_password"]
        self.smtp_tls = config["smtp_tls"]
        self.templates_dir = config["templates_dir"]
        self._add_send_email_admin_middleware()
        self.api.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        backend_dir = os.path.join(os.path.dirname(self.openapi_path), backend_folder_name)
        if not os.path.exists(backend_dir):
            os.makedirs(backend_dir)

        models_path = os.path.join(backend_dir, "models.py")
        routes_path = os.path.join(backend_dir, "routes.py")

        auth_required = False
        for model in self.openapi.models:
            if model.extensions.get(f'x-auth'):
                auth_required = True

        create_models_file(self.openapi_path, models_path, self.openapi.models, self.openapi.excluded_models)
        create_routes_file(routes_path)
        await create_crud_routes(
            self.repository_api_instance,
            self.repository_instance,
            self.openapi,
            models_path,
            routes_path,
            self.jwtSecretKey,
            auth_required,
            self.use_access_rights,
        )

    @staticmethod
    def _read_laia_version(openapi_path: str) -> str:
        laia_config_path = os.path.join(os.path.dirname(openapi_path), "laia.json")
        if not os.path.exists(laia_config_path):
            return "0.1.0"

        try:
            with open(laia_config_path, "r") as laia_config_file:
                return json.load(laia_config_file).get("version", "0.1.0")
        except Exception as e:
            _logger.info(f"Could not read laia.json version: {e}")
            return "0.1.0"

    @staticmethod
    def _parse_constructor_config(args, kwargs):
        config = {
            "use_ontology": False,
            "use_access_rights": True,
            "jwtSecretKey": "secret_key",
            "jwtRefreshSecretKey": None,
            "storage": True,
            "minio_endpoint_url": None,
            "minio_root_user": None,
            "minio_root_password": None,
            "smtp_host": None,
            "smtp_port": None,
            "smtp_user": None,
            "smtp_password": None,
            "smtp_tls": False,
            "templates_dir": None,
            "version": None,
        }
        aliases = {
            "jwt_secret_key": "jwtSecretKey",
            "jwt_refresh_secret_key": "jwtRefreshSecretKey",
        }

        unexpected = set(kwargs) - set(config) - set(aliases)
        if unexpected:
            unexpected_arg = sorted(unexpected)[0]
            raise TypeError(f"LaiaFastApi.__init__() got an unexpected keyword argument '{unexpected_arg}'")

        for key, value in kwargs.items():
            config[aliases.get(key, key)] = value

        if not args:
            return config

        new_signature_fields = [
            "use_ontology",
            "use_access_rights",
            "jwtSecretKey",
            "jwtRefreshSecretKey",
            "storage",
            "minio_endpoint_url",
            "minio_root_user",
            "minio_root_password",
            "smtp_host",
            "smtp_port",
            "smtp_user",
            "smtp_password",
            "smtp_tls",
        ]

        if len(args) == 1 and not isinstance(args[0], bool):
            config["jwtSecretKey"] = args[0]
            return config

        if len(args) > len(new_signature_fields):
            raise TypeError(f"LaiaFastApi.__init__() takes at most {5 + len(new_signature_fields)} positional arguments")

        for key, value in zip(new_signature_fields, args):
            config[key] = value

        return config

    def _add_send_email_admin_middleware(self):
        @self.api.middleware("http")
        async def require_admin_for_send_email(request, call_next):
            if request.method.upper() == "POST" and request.url.path.rstrip("/") == "/send-email":
                authorization = request.headers.get("Authorization", "")
                if not authorization.startswith("Bearer "):
                    return JSONResponse(status_code=401, content={"detail": "Missing or invalid authorization header"})

                token = authorization.replace("Bearer ", "", 1)
                try:
                    payload = verify_jwt_token(token, self.jwtSecretKey)
                except ValueError:
                    return JSONResponse(status_code=401, content={"detail": "Invalid session token"})

                if not await self._payload_has_admin_role(payload):
                    return JSONResponse(status_code=403, content={"detail": "Admin role required"})

            return await call_next(request)

    async def _payload_has_admin_role(self, payload: dict) -> bool:
        user_roles = payload.get("user_roles", [])
        if "admin" in user_roles:
            return True

        for role_id in user_roles:
            try:
                role = await self.repository_instance.get_item("role", role_id)
                if role and role.get("name") == "admin":
                    return True
            except Exception:
                pass

        return False
