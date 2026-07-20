import os
from asyncinit import asyncinit
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from bson.errors import InvalidId
from ...Application.Shared.Utils.CreateModelsFile import create_models_file
from ...Application.Shared.Utils.CreateRoutesFile import create_routes_file
from ...Application.Openapi.CreateRoutes import create_crud_routes
from ...Domain.LaiaBaseModel.ModelRepository import ModelRepository
from ...Domain.Openapi.Openapi import OpenAPI
from ...Domain.Openapi.OpenapiRepository import OpenapiRepository
from ...Domain.Shared.Utils.logger import _logger

@asyncinit
class LaiaFastApi():

    async def __init__(
            self, 
            openapi, 
            backend_folder_name, 
            db, 
            repository: ModelRepository, 
            repositoryAPI: OpenapiRepository, 
            use_ontology: bool, 
            use_access_rights: bool, 
            jwtSecretKey: str='secret_key', 
            jwtRefreshSecretKey: str='secret_refresh', 
            add_storage: bool=True, 
            endpoint_url_storage: str = "", 
            access_key_storage: str = "", 
            secret_key_storage: str = "",
            smtp_host: str = "",
            smtp_port: int = 587,
            smtp_user: str = "",
            smtp_password: str = "",
            smtp_tls: bool = True,
            templates_dir: str = "email_templates",
            hooks_dir: str = "",
            add_geolocation: bool = True):
        
        self.db = db
        self.api = FastAPI(openapi_url='/openapi.json')
        self._setup_custom_openapi()
        self.repository_instance = repository(db)
        self.repository_api_instance = repositoryAPI(self.api, jwtSecretKey, jwtRefreshSecretKey)
        self.openapi_path = openapi
        self.openapi = OpenAPI(openapi)
        self.api.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        @self.api.exception_handler(InvalidId)
        async def invalid_objectid_handler(request: Request, exc: InvalidId):
            return JSONResponse(
                status_code=500,
                content={"msg": f"bson.errors.InvalidId: {str(exc)}"}
            )
        resolved_hooks_dir = hooks_dir or os.path.join(os.path.dirname(templates_dir), "hooks")
        self.smtp_config = {
            "host": smtp_host,
            "port": smtp_port,
            "user": smtp_user,
            "password": smtp_password,
            "tls": smtp_tls,
            "templates_dir": templates_dir,
            "hooks_dir": resolved_hooks_dir
        }

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
            self.openapi, models_path, 
            routes_path, 
            jwtSecretKey, 
            jwtRefreshSecretKey, 
            auth_required, 
            use_access_rights, 
            use_ontology, 
            add_storage, 
            endpoint_url_storage, 
            access_key_storage, 
            secret_key_storage,
            smtp_config=self.smtp_config,
            add_geolocation=add_geolocation)

        # Inject Stats automatically into the LAIA FastApi
        # Note: GeocodingController is already registered via FastAPIOpenapiRepository.create_geolocation_routes
        from ...Framework.Stats.StatsController import StatsController

        user_model_name = None
        for model in self.openapi.models:
            if model.extensions.get(f'x-auth'):
                user_model_name = model.model_name
                break
        
        if user_model_name:
            metrics_file = os.path.join(os.path.dirname(self.openapi_path), "metrics.yaml")
            if not os.path.exists(metrics_file):
                metrics_file = None

            self.api.include_router(
                StatsController(
                    self.repository_instance,
                    user_model_name,
                    metrics_file,
                )
            )

    def _setup_custom_openapi(self):
        api = self.api

        def custom_openapi():
            if api.openapi_schema:
                return api.openapi_schema
            schema = get_openapi(title=api.title, version=api.version, routes=api.routes)
            schemas = schema.get("components", {}).get("schemas", {})
            
            if hasattr(self, 'openapi') and self.openapi:
                orig_models = {m.model_name: m for m in self.openapi.models + self.openapi.laia_models}
                for schema_name, schema_definition in schemas.items():
                    clean_name = schema_name.replace('-Input', '').replace('-Output', '').replace('-Update', '').replace('Update', '')
                    orig_model = orig_models.get(clean_name)
                    if orig_model:
                        for ext_key, ext_val in orig_model.extensions.items():
                            schema_definition[ext_key] = ext_val
                        
                        properties = schema_definition.get('properties', {})
                        field_extensions = orig_model.get_field_extensions()
                        for prop_name, prop_def in properties.items():
                            orig_exts = field_extensions.get(prop_name, {})
                            if isinstance(prop_def, dict):
                                for ext_key, ext_val in orig_exts.items():
                                    prop_def[ext_key] = ext_val

            hidden = {"HTTPValidationError", "ValidationError"}
            schema["components"]["schemas"] = {
                name: s for name, s in schemas.items()
                if name not in hidden
            }
            api.openapi_schema = schema
            return api.openapi_schema

        api.openapi = custom_openapi
