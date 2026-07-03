import pytest
import os
from laiagenlib.Domain.Openapi.Openapi import OpenAPI
from laiagenlib.Domain.Openapi.OpenapiModel import OpenAPIModel

@pytest.fixture
def test_files(request):
    test_dir = os.path.dirname(os.path.abspath(request.module.__file__))
    input_file1 = os.path.join(test_dir, "..", "..", "openapi_files", "api.yaml")
    input_file2 = os.path.join(test_dir, "..", "..", "openapi_files", "api2.yaml")
    input_file3 = os.path.join(test_dir, "..", "..", "openapi_files", "api3.yaml")
    return input_file1, input_file2, input_file3

class TestOpenAPI:
    
    def test_parse_routes(self, test_files):
        input_file1, input_file2, input_file3 = test_files

        parser = OpenAPI(input_file1)
        assert len(parser.routes) == 8

        parser2 = OpenAPI(input_file2)
        assert len(parser2.routes) == 6

        parser3 = OpenAPI(input_file3)
        assert len(parser3.routes) == 1

    def test_create_openapimodel(self, test_files):
        input_file1, _, _ = test_files

        models = []

        pet_properties = {
            'id': {'type': 'string', 'format': 'uuid', 'description': 'Unique identifier for the pet'},
            'name': {'type': 'string', 'description': 'Name of the pet'},
            'species': {'type': 'string', 'description': 'Species of the pet'},
            'owner_id': {'type': 'string', 'format': 'uuid', 'description': 'ID of the owner of the pet'}
        }

        models.append(OpenAPIModel("Pet", pet_properties, []))

        person_properties = {
            'id': {'type': 'string', 'format': 'uuid', 'description': 'Unique identifier for the person', 'x_frontend_editable': False, 'x_frontend_fieldName': 'Id'},
            'name': {'type': 'string', 'description': 'Name of the person', 'x_frontend_fieldName': 'Name', 'x_view_roles': {'type': 'string', 'description': 'Roles required to view this field', 'example': 'admin'}, 'x_edit_roles': {'type': 'string', 'description': 'Roles required to edit this field', 'example': 'admin'}},
            'age': {'type': 'integer', 'description': 'Age of the person'},
            'pets': {'type': 'array', 'items': {'$ref': '#/components/schemas/Pet'}}
        }

        models.append(OpenAPIModel("Person", person_properties, []))

        parser = OpenAPI(input_file1)
        
        assert len(parser.models) == 2
        assert parser.models[0].model_name == models[0].model_name
        assert parser.models[0].properties == models[0].properties
        assert parser.models[1].model_name == models[1].model_name
        assert parser.models[1].properties == models[1].properties

    def test_embedded_models_are_not_root_models(self, tmp_path):
        input_file = tmp_path / "api.yaml"
        input_file.write_text("""
openapi: 3.0.0
info:
  title: Embedded model API
  version: 1.0.0
paths: {}
components:
  schemas:
    User:
      type: object
      properties:
        id:
          type: string
        address:
          x_embedded: true
          $ref: '#/components/schemas/Address'
    Address:
      type: object
      properties:
        street:
          type: string
""")

        parser = OpenAPI(str(input_file))

        assert parser.embedded_model_names == {"Address"}
        assert [model.model_name for model in parser.models] == ["User"]

    def test_permissions_are_parsed(self, tmp_path):
        input_file = tmp_path / "api.yaml"
        input_file.write_text("""
openapi: 3.0.0
info:
  title: Permissions model API
  version: 1.0.0
paths: {}
components:
  schemas:
    Offer:
      type: object
      x-auth: true
      permissions:
        post: ["admin", "user"]
        get: true
        put: true
        patch: true
        delete: true
        search: []
        aggregate: false
      properties:
        id:
          type: string
""")

        parser = OpenAPI(str(input_file))
        offer_model = next(model for model in parser.models if model.model_name == "Offer")
        assert offer_model.extensions.get("x-permissions") == {
            "post": ["admin", "user"],
            "get": True,
            "put": True,
            "patch": True,
            "delete": True,
            "search": [],
            "aggregate": False
        }

