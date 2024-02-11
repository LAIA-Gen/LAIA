import yaml
from fastapi import FastAPI, HTTPException, status
from fastapi.routing import APIRouter
from typing import TypeVar, Optional
import re
from importlib.util import spec_from_file_location, module_from_spec
from .Route import Route
from ..crud.crud import CRUD
from .Model import LaiaBaseModel
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
                        extensions = path_data[method].get('x-', {})
                        self.routes.append(Route(path, method, summary, responses, extensions))

        if 'components' in openapi_spec:
            schemas = openapi_spec['components'].get('schemas', {})
            self.models = list(schemas.keys())

    def create_crud_routes(self, api: FastAPI=None, crud_instance: CRUD=None, models_path: str=""):
        for model_name in self.models:
            model_module = self.import_model(models_path)
            model = getattr(model_module, model_name)
            model_lowercase = model_name.lower()

            create_route = None
            read_route = None
            update_route = None
            delete_route = None
            search_route = None

            for route in self.routes:
                if route.extensions.get(f'x-create-{model_lowercase}'):
                    create_route = route.path
                elif route.extensions.get(f'x-read-{model_lowercase}'):
                    read_route = route.path
                elif route.extensions.get(f'x-update-{model_lowercase}'):
                    update_route = route.path
                elif route.extensions.get(f'x-delete-{model_lowercase}'):
                    delete_route = route.path
                elif route.extensions.get(f'x-search-{model_lowercase}'):
                    search_route = route.path

            self.CRUD(
                api=api,
                model=model,
                create_route=create_route,
                read_route=read_route,
                update_route=update_route,
                delete_route=delete_route,
                search_route=search_route
            )

    def CRUD(self, api: FastAPI, model: T, create_route: Optional[str] = None, read_route: Optional[str] = None, update_route: Optional[str] = None, delete_route: Optional[str] = None, search_route: Optional[str] = None):
        model_name = model.__name__.lower()
        router = APIRouter(tags=[model.__name__])

        def replace_placeholder(route: str) -> str:
            return re.sub(r'\{.*?\}', '{element_id}', route)

        create_route = create_route or f"/{model_name}/"
        read_route = read_route or f"/{model_name}"+"/{element_id}"
        update_route = update_route or f"/{model_name}"+"/{element_id}"
        delete_route = delete_route or f"/{model_name}"+"/{element_id}"
        search_route = search_route or f"/{model_name}s"


        @router.post(create_route, response_model=dict)
        async def create_element(element: model):
            user_roles=["admin"]
            try:
                return await model.create(dict(element), model, user_roles, self.crud_instance)
            except Exception as e:
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

        @router.put(update_route, response_model=dict)
        async def update_element(element_id: str, values: dict):
            user_roles=["admin"]
            try:
                return await model.update(element_id, values, model, user_roles, self.crud_instance)
            except Exception as e:
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
        
        @router.get(read_route, response_model=dict)
        async def read_element(element_id: str):
            user_roles=["admin"]
            try:
                return await model.read(element_id, model, user_roles, self.crud_instance)
            except Exception as e:
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

        @router.delete(delete_route, response_model=str)
        async def delete_element(element_id: str):
            user_roles=["admin"]
            try:
                await model.delete(element_id, model, user_roles, self.crud_instance)
                return f"{model_name} element deleted successfully"
            except Exception as e:
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

        @router.get(search_route, response_model=dict)
        async def search_element(skip: int = 0, limit: int = 10, filters: dict = {}, orders: dict = {}):
            user_roles=["admin"]
            try:
                return await model.search(skip, limit, filters, orders, model, user_roles, self.crud_instance)
            except Exception as e:
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

        api.include_router(router)
    
    def import_model(self, models_path):
        spec = spec_from_file_location("models", models_path)
        module = module_from_spec(spec)
        spec.loader.exec_module(module)
        return module