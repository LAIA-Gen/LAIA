import os
from ...Domain.Openapi.Openapi import OpenAPI
from ...Domain.Openapi.OpenapiRepository import OpenapiRepository
from ...Domain.LaiaBaseModel.ModelRepository import ModelRepository
from ...Domain.Openapi.RoutesInfo import get_routes_info
from ...Domain.Shared.Utils.ImportModel import import_model
from ...Domain.Shared.Utils.logger import _logger

async def create_crud_routes(repositoryAPI: OpenapiRepository=None, repository: ModelRepository=None, openapi: OpenAPI=None, models_path: str="", routes_path: str=""):
    modelsTypes = {}
    for openapiModel in openapi.models:
        model_module = import_model(models_path)
        model = getattr(model_module, openapiModel.model_name)
        modelsTypes[openapiModel.model_name] = model
        model_lowercase = openapiModel.model_name.lower()

        routes_info = get_routes_info(model_lowercase)

        for route in openapi.routes:
            for action in routes_info:
                if route.extensions.get(f'x-{action}-{model_lowercase}') or route.path == routes_info[action]['path']:
                    routes_info[action] = {
                        'path': route.path,
                        'openapi_extra': route.extensions
                    }
                    route.extra = False
                if openapiModel.extensions.get(f'x-auth') and (route.path == f"/auth/register/{model_lowercase}/" or route.path == f"/auth/login/{model_lowercase}/"or route.path == f"/auth/verify/{model_lowercase}/{{token}}"):
                    route.extra = False

        if openapiModel.extensions.get(f'x-auth'):
            await repositoryAPI.create_auth_user_routes(repository, model=model, routes_info=routes_info)
        else:
            await repositoryAPI.create_routes(repository, model=model, routes_info=routes_info)
    
    await repositoryAPI.create_access_rights_routes(models=modelsTypes, repository=repository)
    await repositoryAPI.create_roles_routes(repository)

    # add extra routes

    if os.path.exists(routes_path):
        with open(routes_path, 'r') as f:
            lines = f.readlines()

        all_index = len(lines) 
        for i, line in enumerate(lines):
            if "return router" in line:
                all_index = i
                break

        with open(routes_path, 'w') as f:
            for i, line in enumerate(lines):
                if i == all_index:

                    for route in openapi.routes:
                        if route.extra == True:
                            route_path = route.path.strip('/')
                            function_name = route.method.lower() + '_' + route_path.replace('/', '_').replace('{', '').replace('}', '')
                            if function_name not in ''.join(lines):
                                function_code = f"""    @router.{route.method.lower()}("/{route_path}", openapi_extra={route.extensions})
    async def {function_name}():
        return {{"message": "This is an extra route!"}}

"""
                                f.write(function_code)
                            else:
                                print(f"Function {function_name} already exists in routes.py")

                f.write(line)