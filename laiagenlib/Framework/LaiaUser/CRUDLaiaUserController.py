from fastapi import Body, Depends, HTTPException, status
from fastapi.routing import APIRouter
from fastapi.security import OAuth2PasswordBearer
from typing import TypeVar, Optional, List, Annotated
from ...Application.LaiaUser import JWTToken
from ...Application.LaiaBaseModel import ReadLaiaBaseModel, DeleteLaiaBaseModel, SearchLaiaBaseModel, AggregateLaiaBaseModel
from ...Application.LaiaUser import CreateLaiaUser, UpdateLaiaUser
from ...Domain.LaiaBaseModel.LaiaBaseModel import LaiaBaseModel
from ...Domain.LaiaUser.Role import Role
from ...Domain.LaiaBaseModel.ModelRepository import ModelRepository
from ...Domain.Shared.Utils.logger import _logger
from bson import ObjectId

T = TypeVar('T', bound='LaiaBaseModel')

def CRUDLaiaUserController(repository: ModelRepository=None, model: T=None, model_create: T=None, routes_info: dict=None, jwtSecretKey: str='secret_key', auth_required: bool = False):
    model_name = model.__name__.lower()
    router = APIRouter(tags=[model.__name__])
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
                if isinstance(role, str) and len(role) != 24:
                    user_roles.append(role)
                else:
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

    @router.post(**routes_info['create'], response_model=dict)
    async def create_element(element: model_create, token: get_auth_dependency() = None):
        user_roles = await get_user_roles(repository, token, jwtSecretKey)
        element_dict = element.dict()
        if auth_required:
            element_dict["owner"] = await get_user_id(repository, token, jwtSecretKey)

        element_full = model(**element_dict)
        try:
            return await CreateLaiaUser.create_laia_user(dict(element_full), model, user_roles, repository)
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    @router.put(**routes_info['update'], response_model=dict)
    async def update_element(element_id: str, values: model_create, token: get_auth_dependency() = None):
        user_roles = await get_user_roles(repository, token, jwtSecretKey)
        try:
            return await UpdateLaiaUser.update_laia_user(element_id, values, model, user_roles, repository)
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
        
    @router.get(**routes_info['read'], response_model=dict)
    async def read_element(element_id: str, token: get_auth_dependency() = None):
        user_roles = await get_user_roles(repository, token, jwtSecretKey)
        try:
            return await ReadLaiaBaseModel.read_laia_base_model(element_id, model, user_roles, repository, True)
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    @router.delete(**routes_info['delete'], response_model=str)
    async def delete_element(element_id: str, token: get_auth_dependency() = None):
        user_roles = await get_user_roles(repository, token, jwtSecretKey)
        try:
            await DeleteLaiaBaseModel.delete_laia_base_model(element_id, model, user_roles, repository, True)
            return f"{model_name} element deleted successfully"
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    @router.post(**routes_info['search'], response_model=dict)
    async def search_element(token: get_auth_dependency() = None, skip: int = 0, limit: int = 10, filters: dict = {}, orders: dict = {}):
        user_roles = await get_user_roles(repository, token, jwtSecretKey)
        user_id = ''
        if auth_required:
            user_id = await get_user_id(repository, token, jwtSecretKey)
        try:
            return await SearchLaiaBaseModel.search_laia_base_model(skip, limit, filters, orders, model, user_roles, repository, user_id, True)
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
        
    @router.post(**routes_info['aggregate'], response_model=dict)
    async def aggregate_users(
        pipeline: List[dict] = Body(..., description="Pipeline MongoDB aggregation"),
        token: get_auth_dependency() = None
    ):
        user_roles = await get_user_roles(repository, token, jwtSecretKey)
        user_id = ''
        if auth_required:
            user_id = await get_user_id(repository, token, jwtSecretKey)

        try:
            return await AggregateLaiaBaseModel.aggregate_laia_base_model(
                pipeline, model, user_roles, repository, user_id, True
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )

    return router