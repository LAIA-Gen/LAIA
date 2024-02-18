from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .crud.crud import CRUD
from .models.Openapi import OpenAPI
from .utils.utils import create_models_file, create_flutter_app, create_base_files, call_arg_code_gen
from .utils.logger import _logger
import os

class LaiaFastApi():

    def __init__(self, openapi, db, crud: CRUD):
        self.db = db
        self.crud_instance = crud(db)
        self.openapi_path = openapi
        self.openapi = OpenAPI(openapi)
        self.api = FastAPI(openapi_url='/openapi.json')
        self.api.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        _logger.info("hey")

        models_dir = os.path.join(os.path.dirname(self.openapi_path), "backend")
        if not os.path.exists(models_dir):
            os.makedirs(models_dir)

        models_path = os.path.join(models_dir, "models.py")
        create_models_file(self.openapi_path, models_path)
        self.openapi.create_crud_routes(self.api, self.crud_instance, models_path)
        self.openapi.add_extra_routes(models_dir)

class LaiaFlutter():

    def __init__(self, openapi, app_name: str):
        self.openapi_path = openapi
        self.openapi = OpenAPI(openapi)

        models_dir = os.path.join(os.path.dirname(self.openapi_path), "backend")
        if not os.path.exists(models_dir):
            os.makedirs(models_dir)

        models_path = os.path.join(models_dir, "models.py")
        
        create_flutter_app(app_name)
        create_base_files(app_name)
        app_path = os.path.join(os.path.dirname(self.openapi_path), app_name)
        self.openapi.create_flutter_app(app_name, app_path, models_path)
        call_arg_code_gen(app_name)
