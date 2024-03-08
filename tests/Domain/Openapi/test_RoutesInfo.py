from laiagenlib.Domain.Openapi.RoutesInfo import get_routes_info

def test_get_routes_info():
    expected_result = {
        'create': {
            'path': f"/testmodel/",
            'openapi_extra': {}
        },
        'read': {
            'path': f"/testmodel/{{element_id}}",
            'openapi_extra': {}
        },
        'update': {
            'path': f"/testmodel/{{element_id}}",
            'openapi_extra': {}
        },
        'delete': {
            'path': f"/testmodel/{{element_id}}",
            'openapi_extra': {}
        },
        'search': {
            'path': f"/testmodels/",
            'openapi_extra': {}
        },
    }

    assert get_routes_info("testmodel") == expected_result