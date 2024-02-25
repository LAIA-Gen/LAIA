import yaml
from fastapi import FastAPI, HTTPException, status
from fastapi.routing import APIRouter
from typing import TypeVar
import os
from importlib.util import spec_from_file_location, module_from_spec
from .OpenapiModels import OpenAPIRoute, OpenAPIModel
from ..crud.crud import CRUD
from .Model import LaiaBaseModel
from ..routes.ModelRoutes import ModelCRUD
from ..routes.UserRoutes import AuthRoutes
from .AccessRights import create_access_rights_router
from ..utils.flutter_base_files import home_dart, model_dart
from ..utils.logger import _logger
from ..utils.utils import get_routes_info

T = TypeVar('T', bound='LaiaBaseModel')

class OpenAPI:
    def __init__(self, yaml_path):
        self.yaml_path = yaml_path
        self.routes = []
        self.models = []

        self.parse_yaml()

    def parse_yaml(self):
        with open(self.yaml_path, 'r') as file:
            openapi_spec = yaml.safe_load(file)

        if 'paths' in openapi_spec:
            for path, path_data in openapi_spec['paths'].items():
                methods = path_data.keys()
                for method in methods:
                    if method != "parameters":
                        summary = path_data[method].get('summary', '')
                        responses = path_data[method].get('responses', {})
                        extensions = {k: v for k, v in path_data[method].items() if k.startswith('x-')}
                        if 'AccessRight' not in path_data[method].get('tags', []):
                            self.routes.append(OpenAPIRoute(path, method, summary, responses, extensions, True))

        if 'components' in openapi_spec:
            schemas = openapi_spec['components'].get('schemas', {})
            for schema_name, schema_definition in schemas.items():
                model_name = schema_name
                properties = schema_definition.get('properties', {})
                required_properties = schema_definition.get('required', [])
                extensions = {k: v for k, v in schema_definition.items() if k.startswith('x-')}
                if (model_name != "ValidationError" and model_name != "HTTPValidationError" and model_name != "HTTPException" and not model_name.startswith("Body_search_element_") and not model_name == "Auth"):
                    self.models.append(OpenAPIModel(model_name, properties, required_properties, extensions))

    def create_crud_routes(self, api: FastAPI=None, crud_instance: CRUD=None, models_path: str=""):
        modelsTypes = {}
        for openapiModel in self.models:
            model_module = self.import_model(models_path)
            model = getattr(model_module, openapiModel.model_name)
            modelsTypes[openapiModel.model_name] = model
            model_lowercase = openapiModel.model_name.lower()

            routes_info = get_routes_info(model_lowercase)

            for route in self.routes:
                for action in routes_info:
                    if route.extensions.get(f'x-{action}-{model_lowercase}') or route.path == routes_info[action]['path']:
                        routes_info[action] = {
                            'path': route.path,
                            'openapi_extra': route.extensions
                        }
                        route.extra = False
                    if openapiModel.extensions.get(f'x-auth') and (route.path == f"/auth/register/{model_lowercase}/" or route.path == f"/auth/login/{model_lowercase}/"):
                        route.extra = False

            if openapiModel.extensions.get(f'x-auth'):
                AuthRoutes(
                    api=api,
                    crud_instance=crud_instance,
                    model=model
                )

            ModelCRUD(
                api=api,
                crud_instance=crud_instance,
                model=model,
                routes_info=routes_info
            )
        
        router = APIRouter(tags=["AccessRight"])
        create_access_rights_router(router, modelsTypes, crud_instance) 
        api.include_router(router)

    def add_extra_routes(self, routes_path):
        if os.path.exists(routes_path):
            with open(routes_path, 'r') as f:
                lines = f.readlines()

            all_index = len(lines) 
            for i, line in enumerate(lines):
                if "__all__" in line:
                    all_index = i
                    break

            with open(routes_path, 'w') as f:
                for i, line in enumerate(lines):
                    if i == all_index:

                        for route in self.routes:
                            if route.extra == True:
                                route_path = route.path.strip('/')
                                function_name = route.method.lower() + '_' + route_path.replace('/', '_').replace('{', '').replace('}', '')
                                if function_name not in ''.join(lines):
                                    function_code = f"""@router.{route.method.lower()}("/{route_path}", openapi_extra={route.extensions})
async def {function_name}():
    return {{"message": "This is an extra route!"}}

"""
                                    f.write(function_code)
                                else:
                                    print(f"Function {function_name} already exists in routes.py")

                    f.write(line)

    
    def import_model(self, models_path):
        spec = spec_from_file_location("models", models_path)
        module = module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def create_flutter_app(self, app_name:str, app_path: str, models_path: str=""):
        for openapiModel in self.models:
            model_module = self.import_model(models_path)
            model = getattr(model_module, openapiModel.model_name)
            model_file_content = model_dart(openapiModel, app_name, model)
            with open(os.path.join(app_path, 'lib', 'models', f'{model.__name__.lower()}.dart'), 'w') as f:
                f.write(model_file_content)


        home_file_content = home_dart(app_name, self.models)
        with open(os.path.join(app_path, 'lib', 'screens', 'home.dart'), 'w') as f:
            f.write(home_file_content)
