from typing import TypeVar, Type, Dict
from pydantic import BaseModel
from fastapi import FastAPI
from ...Framework.LaiaBaseModel.CRUDLaiaBaseModelController import CRUDLaiaBaseModelController
from ...Framework.AccessRights.CreateAccessRightsController import create_access_rights_router
from ...Framework.LaiaUser.AuthController import AuthController
from ...Framework.LaiaUser.CRUDLaiaUserController import CRUDLaiaUserController
from ...Framework.LaiaUser.CRUDRoleController import CRUDRoleController
from ...Domain.LaiaBaseModel.ModelRepository import ModelRepository
from ...Domain.Openapi.OpenapiRepository import OpenapiRepository

T = TypeVar('T', bound='BaseModel')

class FastAPIOpenapiRepository(OpenapiRepository):

    def __init__(self, api: any):
        if not isinstance(api, FastAPI):
            raise ValueError("API must be an instance of FastAPI for this implementation")
        self.api = api

    async def create_routes(self, repository: ModelRepository=None, model: T=None, routes_info: dict=None):
        router = CRUDLaiaBaseModelController(repository=repository, model=model, routes_info=routes_info)
        self.api.include_router(router)

    async def create_auth_user_routes(self, repository: ModelRepository=None, model: T=None, routes_info: dict=None):
        auth_router = AuthController(repository=repository, model=model)
        user_router = CRUDLaiaUserController(repository=repository, model=model, routes_info=routes_info)
        self.api.include_router(auth_router)
        self.api.include_router(user_router)

    async def create_access_rights_routes(self, models: Dict[str, Type[BaseModel]], repository: ModelRepository):
        router = create_access_rights_router(models=models, repository=repository)
        self.api.include_router(router)

    async def create_roles_routes(self, repository: ModelRepository=None):
        router = CRUDRoleController(repository=repository)
        self.api.include_router(router)
