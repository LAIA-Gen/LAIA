import bcrypt
from typing import TypeVar, Type, Dict
from pydantic import BaseModel
from fastapi import FastAPI
from ...Framework.LaiaBaseModel.CRUDLaiaBaseModelController import CRUDLaiaBaseModelController
from ...Framework.AccessRights.CRUDAccessRightsController import CRUDAccessRightsController
from ...Framework.LaiaUser.AuthController import AuthController
from ...Framework.LaiaUser.CRUDLaiaUserController import CRUDLaiaUserController
from ...Framework.LaiaUser.CRUDRoleController import CRUDRoleController
from ...Domain.LaiaBaseModel.ModelRepository import ModelRepository
from ...Domain.Openapi.OpenapiRepository import OpenapiRepository
from ...Domain.LaiaUser.Role import Role
from ...Application.LaiaBaseModel.CreateLaiaBaseModel import create_laia_base_model
from ...Application.LaiaBaseModel.SearchLaiaBaseModel import search_laia_base_model

T = TypeVar('T', bound='BaseModel')

class FastAPIOpenapiRepository(OpenapiRepository):

    def __init__(self, api: any, jwtSecretKey: str):
        if not isinstance(api, FastAPI):
            raise ValueError("API must be an instance of FastAPI for this implementation")
        super().__init__(api, jwtSecretKey)

    async def create_routes(self, repository: ModelRepository=None, model: T=None, routes_info: dict=None, jwtSecretKey: str='secret_key', auth_required: bool = False):
        router = CRUDLaiaBaseModelController(repository=repository, model=model, routes_info=routes_info, jwtSecretKey=jwtSecretKey, auth_required=auth_required)
        self.api.include_router(router)

    async def create_auth_user_routes(self, repository: ModelRepository=None, model: T=None, routes_info: dict=None, jwtSecretKey: str='secret_key', auth_required: bool = False):
        # Create a first user
        users = await search_laia_base_model(0, 1, {"email": "admin"}, {}, model, ["admin"], repository)
        if users['items'] == []:
            password =  bcrypt.hashpw("admin".encode('utf-8'), bcrypt.gensalt())
            admin_role = await search_laia_base_model(0, 1, {"name": "admin"}, {}, Role, ["admin"], repository)
            first_user_values = {"name": "Admin", "email": "admin", "roles": [admin_role['items'][0]['id']]}
            await create_laia_base_model({**first_user_values, 'password': password}, model, ["admin"], repository)
        auth_router = AuthController(repository=repository, model=model, jwtSecretKey=jwtSecretKey)
        user_router = CRUDLaiaUserController(repository=repository, model=model, routes_info=routes_info, jwtSecretKey=jwtSecretKey, auth_required=auth_required)
        self.api.include_router(auth_router)
        self.api.include_router(user_router)

    async def create_access_rights_routes(self, models: Dict[str, Type[BaseModel]], repository: ModelRepository, auth_required: bool = False, jwtSecretKey: str='secret_key'):
        router = CRUDAccessRightsController(models=models, repository=repository, jwtSecretKey=jwtSecretKey, auth_required=auth_required)
        self.api.include_router(router)

    async def create_roles_routes(self, repository: ModelRepository=None, auth_required: bool = False, jwtSecretKey: str='secret_key'):
        router = await CRUDRoleController(repository=repository, jwtSecretKey=jwtSecretKey, auth_required=auth_required)
        self.api.include_router(router)
