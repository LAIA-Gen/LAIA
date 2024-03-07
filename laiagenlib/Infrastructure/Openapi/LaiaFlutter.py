import os
from ...Application.Openapi.CreateFlutterApp import create_flutter_app
from ...Application.Shared.Utils.CreateBaseFiles import create_base_files
from ...Application.Shared.Utils.CallFlutterCodeGen import call_flutter_code_gen
from ...Domain.Openapi.Openapi import OpenAPI

class LaiaFlutter():

    def __init__(self, openapi, app_name: str):
        self.openapi_path = openapi
        self.openapi = OpenAPI(openapi)

        models_dir = os.path.join(os.path.dirname(self.openapi_path), "backend")
        if not os.path.exists(models_dir):
            os.makedirs(models_dir)

        models_path = os.path.join(models_dir, "models.py")
        
        create_base_files(app_name, self.openapi.models)
        app_path = os.path.join(os.path.dirname(self.openapi_path), app_name)
        create_flutter_app(self.openapi , app_name, app_path, models_path)
        call_flutter_code_gen(app_name)
