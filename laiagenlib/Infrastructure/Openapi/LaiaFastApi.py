import os
from asyncinit import asyncinit
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
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
            templates_dir: str = "email_templates"):
        
        self.db = db
        self.api = FastAPI(openapi_url='/openapi.json')
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
        self.smtp_config = {
            "host": smtp_host,
            "port": smtp_port,
            "user": smtp_user,
            "password": smtp_password,
            "tls": smtp_tls,
            "templates_dir": templates_dir
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
            smtp_config=self.smtp_config)
