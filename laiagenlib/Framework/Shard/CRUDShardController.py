from typing import Optional, List, Annotated
from bson import ObjectId
from fastapi import APIRouter, HTTPException, status, Depends, Body
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
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
#JMT
def CRUDShardController(repository: ModelRepository, jwtSecretKey: str='secret_key', auth_required: bool = False) -> APIRouter:
    model = Shard
    router = APIRouter(tags=["Shard"])
    http_bearer = HTTPBearer(auto_error=False)

    def get_token(credentials: Optional[HTTPAuthorizationCredentials] = Depends(http_bearer)) -> Optional[str]:
        return credentials.credentials if credentials else None

    class SearchResponse(BaseModel):
        items: List[Shard]
        current_page: int
        max_pages: int
        context: Optional[dict] = Field(None, alias="@context")

    class ErrorResponse(BaseModel):
        detail: str

    def get_auth_dependency():
        if auth_required:
            return Annotated[Optional[str], Depends(get_token)]
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

    @router.post("/shard/", response_model=None, responses={200: {"model": Shard}, 400: {"model": ErrorResponse}, 401: {"model": ErrorResponse}})
    async def create_shard(element: Shard, token: get_auth_dependency() = None):
        user_roles = await get_user_roles(repository, token, jwtSecretKey)
        if "admin" not in user_roles:
            raise HTTPException(status_code=403, detail="Only admin can create shards")
        if auth_required:
            element.owner = await get_user_id(repository, token, jwtSecretKey)
        return await CreateLaiaBaseModel.create_laia_base_model(element, model, user_roles, repository, True)

    @router.put("/shard/{element_id}", response_model=None, responses={200: {"model": Shard}, 401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}})
    async def update_shard(element_id: str, values: Shard, token: get_auth_dependency() = None):
        user_roles = await get_user_roles(repository, token, jwtSecretKey)
        if "admin" not in user_roles:
            raise HTTPException(status_code=403, detail="Only admin can update shards")
        return await UpdateLaiaBaseModel.update_laia_base_model(element_id, values, model, user_roles, repository, True)

    @router.get("/shard/{element_id}", response_model=None, responses={200: {"model": Shard}, 401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}})
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
    @router.post("/shards/", response_model=None, responses={200: {"model": SearchResponse}, 401: {"model": ErrorResponse}})
    async def search_shards(token: get_auth_dependency() = None, skip: int = 0, limit: int = 10, filters: dict = Body({}), orders: dict = Body({}), populate: Optional[List] = Body(None)):
        user_roles = await get_user_roles(repository, token, jwtSecretKey)
        return await SearchLaiaBaseModel.search_laia_base_model(skip, limit, filters, orders, model, user_roles, repository, populate=populate)

    return router