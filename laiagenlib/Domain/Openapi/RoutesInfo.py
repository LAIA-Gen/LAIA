def get_routes_info(model_lowercase: str):
    return {
        'create': {
            'path': f"/{model_lowercase}/",
            'openapi_extra': {}
        },
        'read': {
            'path': f"/{model_lowercase}/{{element_id}}",
            'openapi_extra': {}
        },
        'update': {
            'path': f"/{model_lowercase}/{{element_id}}",
            'openapi_extra': {}
        },
        'delete': {
            'path': f"/{model_lowercase}/{{element_id}}",
            'openapi_extra': {}
        },
        'search': {
            'path': f"/{model_lowercase}s/",
            'openapi_extra': {}
        },
    }
