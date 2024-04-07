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

T = TypeVar('T', bound='BaseModel')

class FastAPIOpenapiRepository(OpenapiRepository):

    def __init__(self, api: any, jwtSecretKey: str):
        if not isinstance(api, FastAPI):
            raise ValueError("API must be an instance of FastAPI for this implementation")
        super().__init__(api, jwtSecretKey)

    async def create_routes(self, repository: ModelRepository=None, model: T=None, routes_info: dict=None):
        router = CRUDLaiaBaseModelController(repository=repository, model=model, routes_info=routes_info)
        self.api.include_router(router)

    async def create_auth_user_routes(self, repository: ModelRepository=None, model: T=None, routes_info: dict=None, jwtSecretKey: str='secret_key'):
        auth_router = AuthController(repository=repository, model=model, jwtSecretKey=jwtSecretKey)
        user_router = CRUDLaiaUserController(repository=repository, model=model, routes_info=routes_info)
        self.api.include_router(auth_router)
        self.api.include_router(user_router)

    async def create_access_rights_routes(self, models: Dict[str, Type[BaseModel]], repository: ModelRepository):
        router = CRUDAccessRightsController(models=models, repository=repository)
        self.api.include_router(router)

    async def create_roles_routes(self, repository: ModelRepository=None):
        router = await CRUDRoleController(repository=repository)
        self.api.include_router(router)
