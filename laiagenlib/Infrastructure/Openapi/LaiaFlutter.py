import os
from asyncinit import asyncinit
from ...Application.Openapi.CreateFlutterApp import create_flutter_app
from ...Application.Shared.Utils.CreateBaseFiles import create_base_files
from ...Domain.Openapi.Openapi import OpenAPI

@asyncinit
class LaiaFlutter():

    async def __init__(self, openapi, backend_folder_name, app_name: str):
        self.openapi_path = openapi
        self.openapi = OpenAPI(openapi)

        models_dir = os.path.join(os.path.dirname(self.openapi_path), backend_folder_name)
        if not os.path.exists(models_dir):
            os.makedirs(models_dir)

        models_path = os.path.join(models_dir, "models.py")
        
        create_base_files(app_name, self.openapi.models)
        app_path = os.path.join(os.path.dirname(self.openapi_path), app_name)
        await create_flutter_app(self.openapi , app_name, app_path, models_path)
