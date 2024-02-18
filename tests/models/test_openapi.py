import pytest
import re
import os
from laiagenlib.models.Openapi import OpenAPI
from laiagenlib.models.OpenapiModels import OpenAPIModel
from laiagenlib.utils.logger import _logger

@pytest.fixture
def test_files(request):
    test_dir = os.path.dirname(os.path.abspath(request.module.__file__))
    input_file1 = os.path.join(test_dir, "..", "openapi_files", "api.yaml")
    input_file2 = os.path.join(test_dir, "..", "openapi_files", "api2.yaml")
    input_file3 = os.path.join(test_dir, "..", "openapi_files", "api3.yaml")
    yield input_file1, input_file2, input_file3

def test_parse_routes(test_files):
    input_file1, input_file2, input_file3 = test_files

    parser = OpenAPI(input_file1)
    assert len(parser.routes) == 8
    _logger.info("HEY")
    _logger.info(parser.routes[1].method)
    _logger.info(parser.routes[1].path)
    _logger.info(parser.routes[1].extensions)

    parser2 = OpenAPI(input_file2)
    assert len(parser2.routes) == 6

    parser3 = OpenAPI(input_file3)
    assert len(parser3.routes) == 1

def test_parse_models(test_files):
    properties = {
        'id': {'type': 'string', 'format': 'uuid', 'description': 'Unique identifier for the person', 'x-frontend-editable': False, 'x-frontend-fieldName': 'Id'},
        'name': {'type': 'string', 'description': 'Name of the person', 'x-frontend-fieldName': 'Name', 'x-view-roles': {'type': 'string', 'description': 'Roles required to view this field', 'example': 'admin'}, 'x-edit-roles': {'type': 'string', 'description': 'Roles required to edit this field', 'example': 'admin'}},
        'age': {'type': 'integer', 'description': 'Age of the person'},
        'pets': {'type': 'array', 'items': {'$ref': '#/components/schemas/Pet'}}
    }

    model = OpenAPIModel("Person", properties, ["id", "name"])
    frontend_props = model.find_frontend_properties()
    assert frontend_props == {'id': {'editable': False, 'fieldName': 'Id'}, 'name': {'fieldName': 'Name'}}
    