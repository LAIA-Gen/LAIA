import yaml
from fastapi import FastAPI, HTTPException, status
from fastapi.routing import APIRouter
from typing import TypeVar, Optional
import re
import os
from importlib.util import spec_from_file_location, module_from_spec
from .OpenapiModels import OpenAPIRoute, OpenAPIModel
from ..crud.crud import CRUD
from .Model import LaiaBaseModel
from ..utils.flutter_base_files import home_dart, model_dart
from ..utils.logger import _logger

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
                        self.routes.append(OpenAPIRoute(path, method, summary, responses, extensions))

        if 'components' in openapi_spec:
            schemas = openapi_spec['components'].get('schemas', {})
            for schema_name, schema_definition in schemas.items():
                model_name = schema_name
                properties = schema_definition.get('properties', {})
                required_properties = schema_definition.get('required', [])
                if (model_name != "ValidationError" and model_name != "HTTPValidationError" and model_name != "HTTPException" and not model_name.startswith("Body_search_element_")):
                    self.models.append(OpenAPIModel(model_name, properties, required_properties))

    def create_crud_routes(self, api: FastAPI=None, crud_instance: CRUD=None, models_path: str=""):
        for openapiModel in self.models:
            model_module = self.import_model(models_path)
            model = getattr(model_module, openapiModel.model_name)
            model_lowercase = openapiModel.model_name.lower()

            routes_info = {
                'create': None,
                'read': None,
                'update': None,
                'delete': None,
                'search': None
            }

            for route in self.routes:
                for action in routes_info:
                    if route.extensions.get(f'x-{action}-{model_lowercase}'):
                        routes_info[action] = {
                            'path': route.path,
                            'openapi_extra': route.extensions
                        }

            self.CRUD(
                api=api,
                crud_instance=crud_instance,
                model=model,
                routes_info=routes_info
            )

    def CRUD(self, api: FastAPI, crud_instance: CRUD=None, model: T=None, routes_info: dict=None):
        model_name = model.__name__.lower()
        router = APIRouter(tags=[model.__name__])

        def get_route_info(action: str):
            route_info = routes_info.get(action, {})
            if route_info:
                return {'path': route_info.get('path', f"/{model_name}/"), 'openapi_extra': route_info.get('openapi_extra', {})}
            return None

        @router.post(**get_route_info('create') or {'path': f"/{model_name}/"}, response_model=dict)
        async def create_element(element: model):
            user_roles=["admin"]
            try:
                return await model.create(dict(element), model, user_roles, crud_instance)
            except Exception as e:
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

        @router.put(**get_route_info('update') or {'path': f"/{model_name}/{{element_id}}"}, response_model=dict)
        async def update_element(element_id: str, values: dict):
            user_roles=["admin"]
            try:
                return await model.update(element_id, values, model, user_roles, crud_instance)
            except Exception as e:
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
            
        @router.get(**get_route_info('read') or {'path': f"/{model_name}/{{element_id}}"}, response_model=dict)
        async def read_element(element_id: str):
            user_roles=["admin"]
            try:
                return await model.read(element_id, model, user_roles, crud_instance)
            except Exception as e:
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

        @router.delete(**get_route_info('delete') or {'path': f"/{model_name}/{{element_id}}"}, response_model=str)
        async def delete_element(element_id: str):
            user_roles=["admin"]
            try:
                await model.delete(element_id, model, user_roles, crud_instance)
                return f"{model_name} element deleted successfully"
            except Exception as e:
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

        @router.post(**get_route_info('search') or {'path': f"/{model_name}s"}, response_model=dict)
        async def search_element(skip: int = 0, limit: int = 10, filters: dict = {}, orders: dict = {}):
            user_roles=["admin"]
            try:
                return await model.search(skip, limit, filters, orders, model, user_roles, crud_instance)
            except Exception as e:
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

        api.include_router(router)

    def add_extra_routes(self, models_path):
        extra_routes_code = ""
        for route in self.routes:
            route_path = route.path.strip('/')
            function_name = route.method.lower() + '_' + route_path.replace('/', '_')
            function_code = f"""
@router.{route.method.lower()}("/{route_path}")
async def {function_name}():
return {{"message": "This is an extra route!"}}
"""
            extra_routes_code += function_code

        routes_file_path = os.path.join(models_path, 'routes.py')
        if os.path.exists(routes_file_path):
            with open(routes_file_path, 'r') as f:
                existing_code = f.read()
                if extra_routes_code in existing_code:
                    print("Extra routes already exist in routes.py")
                    return

        with open(routes_file_path, 'a') as f:
            f.write(extra_routes_code)
    
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
