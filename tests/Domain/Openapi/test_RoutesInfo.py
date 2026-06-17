from laiagenlib.Domain.Openapi.RoutesInfo import get_routes_info

def test_get_routes_info():
    expected_result = {
        'create': {
            'path': f"/testmodel/",
            'summary': 'Create Testmodel',
            'description': 'Create a new Testmodel element.',
            'openapi_extra': {}
        },
        'read': {
            'path': f"/testmodel/{{element_id}}",
            'summary': 'Read Testmodel',
            'description': 'Read an existing Testmodel element by id.',
            'openapi_extra': {}
        },
        'update': {
            'path': f"/testmodel/{{element_id}}",
            'summary': 'Update Testmodel',
            'description': 'Update an existing Testmodel element by id.',
            'openapi_extra': {}
        },
        'delete': {
            'path': f"/testmodel/{{element_id}}",
            'summary': 'Delete Testmodel',
            'description': 'Delete an existing Testmodel element by id.',
            'openapi_extra': {}
        },
        'search': {
            'path': f"/testmodels/",
            'summary': 'Search Testmodel',
            'description': 'Search Testmodel elements.',
            'openapi_extra': {}
        },
    }

    assert get_routes_info("testmodel") == expected_result
