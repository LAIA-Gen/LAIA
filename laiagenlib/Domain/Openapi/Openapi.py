from typing import TypeVar, List
import yaml
from ..LaiaBaseModel.LaiaBaseModel import LaiaBaseModel
from .OpenapiModel import OpenAPIModel
from .OpenapiRoute import OpenAPIRoute
from ...Domain.Shared.Utils.logger import _logger

T = TypeVar('T', bound='LaiaBaseModel')

class OpenAPI:
    yaml_path: str 
    routes: List[OpenAPIRoute]
    models: List[OpenAPIModel]
    laia_models: List[OpenAPIModel]
    excluded_models: List[str] = [
        "AccessRight", 
        "Auth",
        "Role",
        "Type",  
        "Point",
        "GeometryPoint",
        "LineString",
        "GeometryLineString",
        "Polygon",
        "GeometryPolygon",
        "MultiPoint", 
        "GeometryMultiPoint",
        "MultiLineString", 
        "GeometryMultiLineString",
        "MultiPolygon", 
        "GeometryMultiPolygon",
        "Geometry", 
        "Feature",
        "ValidationError", 
        "HTTPValidationError", 
        "HTTPException"
    ]

    def __init__(self, yaml_path):
        self.yaml_path = yaml_path
        self.routes = []
        self.models = []
        self.laia_models = []

        with open(self.yaml_path, 'r') as file:
            openapi_spec = yaml.safe_load(file)

        self.parse_yaml(openapi_spec)

    def parse_yaml(self, openapi_spec):
        if 'paths' in openapi_spec:
            for path, path_data in openapi_spec['paths'].items():
                methods = path_data.keys()
                for method in methods:
                    if method != "parameters":
                        summary = path_data[method].get('summary', '')
                        responses = path_data[method].get('responses', {})
                        extensions = {k: v for k, v in path_data[method].items() if k.startswith('x-')}
                        if 'AccessRight' not in path_data[method].get('tags', []) and 'Role' not in path_data[method].get('tags', []):
                            self.routes.append(OpenAPIRoute(path, method, summary, responses, extensions, True))

        if 'components' in openapi_spec:
            schemas = openapi_spec['components'].get('schemas', {})
            for schema_name, schema_definition in schemas.items():
                model_name = schema_name
                properties = schema_definition.get('properties', {})
                required_properties = schema_definition.get('required', [])
                extensions = {k: v for k, v in schema_definition.items() if k.startswith('x-')}
                if (model_name in ['AccessRight', 'Role']):
                    self.laia_models.append(OpenAPIModel(model_name, properties, required_properties, extensions))
                if (model_name not in self.excluded_models and not model_name.startswith("Body_search_element_") and not model_name.startswith("Body_search_access_rights_")):
                    self.models.append(OpenAPIModel(model_name, properties, required_properties, extensions))
                    