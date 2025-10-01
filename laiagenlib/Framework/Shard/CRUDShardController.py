from typing import Optional, List, Annotated
from bson import ObjectId
from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer
from ...Domain.LaiaUser.Role import Role

from ...Application.LaiaBaseModel import (
    CreateLaiaBaseModel,
    ReadLaiaBaseModel,
    DeleteLaiaBaseModel,
    SearchLaiaBaseModel,
    UpdateLaiaBaseModel
)
from ...Application.LaiaUser import JWTToken
from ...Domain.LaiaBaseModel.ModelRepository import ModelRepository
from ...Domain.Shared.Utils.logger import _logger

from ...Domain.Shard.Shard import Shard

def CRUDShardController(repository: ModelRepository, jwtSecretKey: str='secret_key', auth_required: bool = False) -> APIRouter:
    model = Shard
    router = APIRouter(tags=["Shard"])
    oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

    def get_auth_dependency():
        if auth_required:
            return Annotated[Optional[str], Depends(oauth2_scheme)]
        else:
            return Optional[str]

    async def get_user_roles(repository: ModelRepository=None, token: Optional[str] = None, jwtSecretKey: str = 'secret_key') -> List[str]:
        if not token:
            if auth_required:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing or invalid authorization header")
            else:
                return ["admin"]

        try:
            payload = JWTToken.verify_jwt_token(token, jwtSecretKey)
            _logger.info(payload)
            
            user_roles_ids = payload.get("user_roles", [])
            _logger.info(user_roles_ids)
            user_roles = []
            for role in user_roles_ids:
                user_role = await ReadLaiaBaseModel.read_laia_base_model(role, Role, ['admin'], repository, False)
                user_roles.append(user_role['name'])

        except ValueError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session token")
        
        return user_roles
    
    async def get_user_id(repository: ModelRepository=None, token: Optional[str] = None, jwtSecretKey: str = 'secret_key') -> List[str]:
        if not token:
            if auth_required:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing or invalid authorization header")
            else:
                return ["admin"]

        try:
            payload = JWTToken.verify_jwt_token(token, jwtSecretKey)
            user_id = payload.get("user_id", [])

        except ValueError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session token")
        
        return ObjectId(user_id)

    @router.post("/shard/", response_model=dict)
    async def create_shard(element: Shard, token: get_auth_dependency() = None):
        user_roles = await get_user_roles(repository, token, jwtSecretKey)
        if "admin" not in user_roles:
            raise HTTPException(status_code=403, detail="Only admin can create shards")
        if auth_required:
            element.owner = await get_user_id(repository, token, jwtSecretKey)
        return await CreateLaiaBaseModel.create_laia_base_model(element, model, user_roles, repository, True)

    @router.put("/shard/{element_id}", response_model=dict)
    async def update_shard(element_id: str, values: Shard, token: get_auth_dependency() = None):
        user_roles = await get_user_roles(repository, token, jwtSecretKey)
        if "admin" not in user_roles:
            raise HTTPException(status_code=403, detail="Only admin can update shards")
        return await UpdateLaiaBaseModel.update_laia_base_model(element_id, values, model, user_roles, repository, True)

    @router.get("/shard/{element_id}", response_model=dict)
    async def read_shard(element_id: str, token: get_auth_dependency() = None):
        user_roles = await get_user_roles(repository, token, jwtSecretKey)
        return await ReadLaiaBaseModel.read_laia_base_model(element_id, model, user_roles, repository, True)

    @router.delete("/shard/{element_id}", response_model=str)
    async def delete_shard(element_id: str, token: get_auth_dependency() = None):
        user_roles = await get_user_roles(repository, token, jwtSecretKey)
        if "admin" not in user_roles:
            raise HTTPException(status_code=403, detail="Only admin can delete shards")
        await DeleteLaiaBaseModel.delete_laia_base_model(element_id, model, user_roles, repository, True)
        return "Shard deleted successfully"

    @router.post("/shards/", response_model=dict)
    async def search_shards(token: get_auth_dependency() = None, skip: int = 0, limit: int = 10, filters: dict = {}, orders: dict = {}):
        user_roles = await get_user_roles(repository, token, jwtSecretKey)
        return await SearchLaiaBaseModel.search_laia_base_model(skip, limit, filters, orders, model, user_roles, repository)

    return router