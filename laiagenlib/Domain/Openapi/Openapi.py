import yaml
from fastapi import FastAPI, HTTPException, status
from fastapi.routing import APIRouter
from typing import TypeVar
import os
from importlib.util import spec_from_file_location, module_from_spec
from .OpenapiModels import OpenAPIRoute, OpenAPIModel
from ..crud.crud import CRUD
from .Model import LaiaBaseModel
from ..models.OpenapiModels import OpenAPIRoute, OpenapiModel
from ..routes.ModelRoutes import ModelCRUD
from ..routes.UserRoutes import AuthRoutes
from .AccessRights import create_access_rights_router
from ..utils.flutter_base_files import home_dart, model_dart
from ..utils.logger import _logger
from ..utils.utils import get_routes_info

T = TypeVar('T', bound='LaiaBaseModel')

class OpenAPI:
    yaml_path: str
    routes: List[OpenAPIRoute]
    models: List[OpenAPIModel]

    def __init__(self, yaml_path):
        self.yaml_path = yaml_path
        self.routes = []
        self.models = []
