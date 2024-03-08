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

    async def __init__(self, openapi, db, repository: ModelRepository, repositoryAPI: OpenapiRepository):
        self.db = db
        self.api = FastAPI(openapi_url='/openapi.json')
        self.repository_instance = repository(db)
        self.repository_api_instance = repositoryAPI(self.api)
        self.openapi_path = openapi
        self.openapi = OpenAPI(openapi)
        self.api.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        backend_dir = os.path.join(os.path.dirname(self.openapi_path), "backend")
        if not os.path.exists(backend_dir):
            os.makedirs(backend_dir)

        models_path = os.path.join(backend_dir, "models.py")
        routes_path = os.path.join(backend_dir, "routes.py")
        create_models_file(self.openapi_path, models_path, self.openapi.models)
        create_routes_file(routes_path)
        await create_crud_routes(self.repository_api_instance, self.repository_instance, self.openapi, models_path, routes_path)
