from typing import TypeVar, Type, Dict
from pydantic import BaseModel
from ..LaiaBaseModel.ModelRepository import ModelRepository

T = TypeVar('T', bound='BaseModel')

class OpenapiRepository:

    def __init__(self, api: any, jwtSecretKey: str):
        self.api = api
        self.jwtSecretKey = jwtSecretKey

    async def create_routes(repository: ModelRepository=None, model: T=None, routes_info: dict=None):
        pass

    async def create_auth_user_routes(repository: ModelRepository=None, model: T=None, routes_info: dict=None, jwtSecretKey: str='secret_key'):
        pass

    async def create_access_rights_routes(models: Dict[str, Type[BaseModel]], repository: ModelRepository):
        pass

    async def create_roles_routes(repository: ModelRepository=None):
        pass
