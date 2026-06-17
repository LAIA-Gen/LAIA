def get_routes_info(model_lowercase: str):
    model_name = model_lowercase.replace("_", " ").title()
    return {
        'create': {
            'path': f"/{model_lowercase}/",
            'summary': f"Create {model_name}",
            'description': f"Create a new {model_name} element.",
            'openapi_extra': {}
        },
        'read': {
            'path': f"/{model_lowercase}/{{element_id}}",
            'summary': f"Read {model_name}",
            'description': f"Read an existing {model_name} element by id.",
            'openapi_extra': {}
        },
        'update': {
            'path': f"/{model_lowercase}/{{element_id}}",
            'summary': f"Update {model_name}",
            'description': f"Update an existing {model_name} element by id.",
            'openapi_extra': {}
        },
        'delete': {
            'path': f"/{model_lowercase}/{{element_id}}",
            'summary': f"Delete {model_name}",
            'description': f"Delete an existing {model_name} element by id.",
            'openapi_extra': {}
        },
        'search': {
            'path': f"/{model_lowercase}s/",
            'summary': f"Search {model_name}",
            'description': f"Search {model_name} elements.",
            'openapi_extra': {}
        },
    }
