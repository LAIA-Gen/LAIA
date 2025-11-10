from typing import TypeVar, Type, Dict
from pydantic import BaseModel
from ..LaiaBaseModel.ModelRepository import ModelRepository

T = TypeVar('T', bound='BaseModel')

class OpenapiRepository:

    def __init__(self, api: any, jwtSecretKey: str, jwtRefreshSecretKey: str):
        self.api = api
        self.jwtSecretKey = jwtSecretKey
        self.jwtRefreshSecretKey = jwtRefreshSecretKey

    async def create_routes(repository: ModelRepository=None, model: T=None, routes_info: dict=None, use_access_rights: bool=True, use_ontology: bool=False):
        pass

    async def create_storage_routes(endpoint_url: str, access_key: str, secret_key: str):
        pass

    async def create_auth_user_routes(repository: ModelRepository=None, model: T=None, routes_info: dict=None, jwtSecretKey: str='secret_key', jwtRefreshSecretKey: str='secret_refresh', smtp_config: dict = None):
        pass

    async def create_access_rights_routes(models: Dict[str, Type[BaseModel]], repository: ModelRepository):
        pass

    async def create_shard_routes(models: Dict[str, Type[BaseModel]], repository: ModelRepository):
        pass

    async def create_roles_routes(repository: ModelRepository=None):
        pass

    async def create_email_routes(smtp_config: dict = None):
        pass
