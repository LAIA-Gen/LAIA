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
    embedded_model_names: set
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
        self.embedded_model_names = set()

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
            self.embedded_model_names = self._get_embedded_model_names(schemas)
            for schema_name, schema_definition in schemas.items():
                model_name = schema_name
                properties = schema_definition.get('properties', {})
                required_properties = schema_definition.get('required', [])
                extensions = {k: v for k, v in schema_definition.items() if k.startswith('x-')}
                if (model_name in ['AccessRight', 'Role']):
                    self.laia_models.append(OpenAPIModel(model_name, properties, required_properties, extensions))
                if (model_name not in self.excluded_models and model_name not in self.embedded_model_names and not model_name.startswith("Body_search_element_") and not model_name.startswith("Body_search_access_rights_")):
                    self.models.append(OpenAPIModel(model_name, properties, required_properties, extensions))

    @staticmethod
    def _is_embedded_property(prop_definition):
        return isinstance(prop_definition, dict) and (
            prop_definition.get('x_embedded') or prop_definition.get('x-embedded')
        )

    @staticmethod
    def _get_ref_model_names(prop_definition):
        ref_names = []
        if not isinstance(prop_definition, dict):
            return ref_names

        ref = prop_definition.get('$ref')
        if isinstance(ref, str) and ref.startswith('#/components/schemas/'):
            ref_names.append(ref.rsplit('/', 1)[-1])

        items = prop_definition.get('items')
        if isinstance(items, dict):
            ref_names.extend(OpenAPI._get_ref_model_names(items))

        for key in ('anyOf', 'oneOf', 'allOf'):
            for option in prop_definition.get(key, []):
                ref_names.extend(OpenAPI._get_ref_model_names(option))

        return ref_names

    @staticmethod
    def _get_embedded_model_names(schemas):
        embedded_model_names = set()
        for schema_definition in schemas.values():
            properties = schema_definition.get('properties', {})
            for prop_definition in properties.values():
                if OpenAPI._is_embedded_property(prop_definition):
                    embedded_model_names.update(OpenAPI._get_ref_model_names(prop_definition))
        return embedded_model_names
