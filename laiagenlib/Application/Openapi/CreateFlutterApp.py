import os
from ...Domain.Openapi.Openapi import OpenAPI
from ...Domain.Shared.Utils.ImportModel import import_model
from ...Domain.Openapi.FlutterBaseFiles import model_dart, home_dart

def create_flutter_app(openapi: OpenAPI=None, app_name:str="", app_path: str="", models_path: str=""):
    for openapiModel in openapi.models:
        model_module = import_model(models_path)
        model = getattr(model_module, openapiModel.model_name)
        model_file_content = model_dart(openapiModel, app_name, model)
        with open(os.path.join(app_path, 'lib', 'models', f'{model.__name__.lower()}.dart'), 'w') as f:
            f.write(model_file_content)


    home_file_content = home_dart(app_name, openapi.models)
    with open(os.path.join(app_path, 'lib', 'screens', 'home.dart'), 'w') as f:
        f.write(home_file_content)
