import os
from ...Domain.Openapi.Openapi import OpenAPI
from ...Domain.Openapi.OpenapiRepository import OpenapiRepository
from ...Domain.LaiaBaseModel.ModelRepository import ModelRepository
from ...Domain.Openapi.RoutesInfo import get_routes_info
from ...Domain.Shared.Utils.ImportModel import import_model
from ...Domain.Shared.Utils.logger import _logger

async def create_crud_routes(
        repositoryAPI: OpenapiRepository=None, 
        repository: ModelRepository=None, 
        openapi: OpenAPI=None, 
        models_path: str="", 
        routes_path: str="", 
        jwtSecretKey: str='secret_key', 
        jwtRefreshSecretKey: str='secret_refresh', 
        auth_required: bool = False, 
        use_access_rights: bool = True, 
        use_ontology: bool = False, 
        add_storage: bool = True, 
        endpoint_url_storage: str = "", 
        access_key_storage: str = "", 
        secret_key_storage: str = "", 
        smtp_config: dict = None):
    
    await repositoryAPI.create_roles_routes(repository, jwtSecretKey=jwtSecretKey, auth_required=auth_required)

    modelsTypes = {}
    for openapiModel in openapi.models:
        model_module = import_model(models_path)
        model = getattr(model_module, openapiModel.model_name)

        update_model_name = f"{openapiModel.model_name}Update"
        update_model = getattr(model_module, update_model_name, None)

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
            await repositoryAPI.create_auth_user_routes(repository, model=model, update_model=update_model, routes_info=routes_info, jwtSecretKey=jwtSecretKey, jwtRefreshSecretKey=jwtRefreshSecretKey, auth_required=auth_required, use_access_rights=use_access_rights, smtp_config=smtp_config)
        else:
            await repositoryAPI.create_routes(repository, model=model, update_model=update_model, routes_info=routes_info, jwtSecretKey=jwtSecretKey, auth_required=auth_required, use_access_rights=use_access_rights, use_ontology=use_ontology)

        if add_storage == True:
            await repositoryAPI.create_storage_routes(endpoint_url_storage, access_key_storage, secret_key_storage)

    if use_access_rights: 
        await repositoryAPI.create_access_rights_routes(models=modelsTypes, repository=repository, jwtSecretKey=jwtSecretKey, auth_required=auth_required)

    await repositoryAPI.create_shard_routes(models=modelsTypes, repository=repository, jwtSecretKey=jwtSecretKey, auth_required=auth_required)

    if smtp_config and smtp_config.get("host"):
        await repositoryAPI.create_email_routes(smtp_config)

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