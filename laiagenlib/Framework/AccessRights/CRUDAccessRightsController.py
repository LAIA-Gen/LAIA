from typing import TypeVar, Optional, List, Annotated, Dict, Type
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, status, Depends, Body
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from ...Application.LaiaBaseModel import ReadLaiaBaseModel, DeleteLaiaBaseModel, SearchLaiaBaseModel, UpdateLaiaBaseModel
from ...Application.AccessRights import CreateAccessRights, UpdateAccessRights
from ...Application.LaiaUser import JWTToken
from ...Domain.AccessRights.AccessRights import AccessRight
from ...Domain.LaiaUser.Role import Role
from ...Domain.LaiaBaseModel.ModelRepository import ModelRepository
from ...Domain.Shared.Utils.logger import _logger
#JMT
def CRUDAccessRightsController(models: Dict[str, Type[BaseModel]], repository: ModelRepository, jwtSecretKey: str='secret_key', auth_required: bool = False) -> APIRouter:
    model = AccessRight
    router = APIRouter(tags=["AccessRight"])
    http_bearer = HTTPBearer(auto_error=False)

    def get_token(credentials: Optional[HTTPAuthorizationCredentials] = Depends(http_bearer)) -> Optional[str]:
        return credentials.credentials if credentials else None

    class SearchResponse(BaseModel):
        items: List[AccessRight]
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

    @router.post("/accessright/", response_model=None, responses={200: {"model": AccessRight}, 400: {"model": ErrorResponse}, 401: {"model": ErrorResponse}})
    async def create_access_rights_route(new_access_rights: AccessRight, token: get_auth_dependency() = None):
        user_roles = await get_user_roles(repository, token, jwtSecretKey)
        model = None
        for key in models.keys():
            if key.lower() == new_access_rights.model:
                model = models[key]
                break
        if not model:
            raise HTTPException(status_code=404, detail="Model not found")
        try:
            return await CreateAccessRights.create_access_rights(repository, dict(new_access_rights), model, user_roles)
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    @router.put("/accessright/{element_id}", response_model=None, responses={200: {"model": AccessRight}, 401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}})
    async def update_access_rights(element_id: str, values: dict, token: get_auth_dependency() = None):
        user_roles = await get_user_roles(repository, token, jwtSecretKey)
        try:
            return await UpdateAccessRights.update_access_rights(element_id, repository, values, model, user_roles)
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
        
    @router.get("/accessright/{element_id}", response_model=None, responses={200: {"model": AccessRight}, 401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}})
    async def read_access_rights(element_id: str, token: get_auth_dependency() = None):
        user_roles = await get_user_roles(repository, token, jwtSecretKey)
        try:
            return await ReadLaiaBaseModel.read_laia_base_model(element_id, model, user_roles, repository)
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    @router.delete("/accessright/{element_id}", response_model=str)
    async def delete_access_rights(element_id: str, token: get_auth_dependency() = None):
        user_roles = await get_user_roles(repository, token, jwtSecretKey)
        try:
            await DeleteLaiaBaseModel.delete_laia_base_model(element_id, model, user_roles, repository)
            return f"AccessRight deleted successfully"
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    @router.post("/accessrights/", response_model=None, responses={200: {"model": SearchResponse}, 401: {"model": ErrorResponse}})
    async def search_access_rights(token: get_auth_dependency() = None, skip: int = 0, limit: int = 10, filters: dict = Body({}), orders: dict = Body({}), populate: Optional[List] = Body(None)):
        user_roles = await get_user_roles(repository, token, jwtSecretKey)
        try:
            return await SearchLaiaBaseModel.search_laia_base_model(skip, limit, filters, orders, model, user_roles, repository, populate=populate)
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    return router