from typing import TypeVar, Type, Dict
from pydantic import BaseModel
from ..LaiaBaseModel.ModelRepository import ModelRepository

T = TypeVar('T', bound='BaseModel')

class OpenapiRepository:

    def __init__(self, api: any, jwtSecretKey: str, jwtRefreshSecretKey: str):
        self.api = api
        self.jwtSecretKey = jwtSecretKey
        self.jwtRefreshSecretKey = jwtRefreshSecretKey

    async def create_routes(repository: ModelRepository=None, model: T=None, model_create: T = None, routes_info: dict=None, use_access_rights: bool=True, use_ontology: bool=False):
        pass

    async def create_auth_user_routes(repository: ModelRepository=None, model: T=None, model_create: T = None, routes_info: dict=None, jwtSecretKey: str='secret_key', jwtRefreshSecretKey: str='secret_refresh'):
        pass

    async def create_access_rights_routes(models: Dict[str, Type[BaseModel]], repository: ModelRepository):
        pass

    async def create_roles_routes(repository: ModelRepository=None):
        pass
