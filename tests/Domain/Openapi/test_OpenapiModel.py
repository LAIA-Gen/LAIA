from laiagenlib.Domain.Openapi.OpenapiModel import OpenAPIModel

def test_create_openapimodel():
    properties = {
        'id': {'type': 'string', 'format': 'uuid', 'description': 'Unique identifier for the person', 'x_frontend_editable': False, 'x_frontend_fieldName': 'Id'},
        'name': {'type': 'string', 'description': 'Name of the person', 'x_frontend_fieldName': 'Name', 'x_view_roles': {'type': 'string', 'description': 'Roles required to view this field', 'example': 'admin'}, 'x_edit_roles': {'type': 'string', 'description': 'Roles required to edit this field', 'example': 'admin'}},
        'age': {'type': 'integer', 'description': 'Age of the person'},
        'pets': {'type': 'array', 'items': {'$ref': '#/components/schemas/Pet'}}
    }

    model = OpenAPIModel("Person", properties, ["id", "name"])
    frontend_props = model.get_frontend_properties()
    extensions = model.get_field_extensions()
    assert frontend_props == {'id': {'editable': False, 'fieldName': 'Id'}, 'name': {'fieldName': 'Name'}}
    assert extensions == {'id': {'x_frontend_editable': False, 'x_frontend_fieldName': 'Id'}, 'name': {'x_frontend_fieldName': 'Name', 'x_view_roles': {'type': 'string', 'description': 'Roles required to view this field', 'example': 'admin'}, 'x_edit_roles': {'type': 'string', 'description': 'Roles required to edit this field', 'example': 'admin'}}}
