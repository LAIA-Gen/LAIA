from fastapi import Depends, HTTPException, status
from fastapi.routing import APIRouter
from fastapi.security import OAuth2PasswordBearer
from typing import TypeVar, Optional, List, Annotated
from ...Application.LaiaBaseModel import ReadLaiaBaseModel, CreateLaiaBaseModel, DeleteLaiaBaseModel, SearchLaiaBaseModel, UpdateLaiaBaseModel
from ...Application.LaiaUser import JWTToken
from ...Domain.LaiaBaseModel.LaiaBaseModel import LaiaBaseModel
from ...Domain.LaiaUser.Role import Role
from ...Domain.LaiaBaseModel.ModelRepository import ModelRepository
from ...Domain.Shared.Utils.logger import _logger

T = TypeVar('T', bound='LaiaBaseModel')

def CRUDLaiaBaseModelController(repository: ModelRepository=None, model: T=None, routes_info: dict=None, jwtSecretKey: str='secret_key'):
    model_name = model.__name__.lower()
    router = APIRouter(tags=[model.__name__])
    oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

    @router.post(**routes_info['create'], response_model=dict)
    async def create_element(element: model, token: Annotated[str, Depends(oauth2_scheme)]):
        user_roles = await get_user_roles(repository, token, jwtSecretKey)
        _logger.info(user_roles)
        try:
            return await CreateLaiaBaseModel.create_laia_base_model(dict(element), model, user_roles, repository)
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    @router.put(**routes_info['update'], response_model=dict)
    async def update_element(element_id: str, values: dict, token: Annotated[str, Depends(oauth2_scheme)]):
        user_roles = await get_user_roles(repository, token, jwtSecretKey)
        _logger.info(user_roles)
        try:
            return await UpdateLaiaBaseModel.update_laia_base_model(element_id, values, model, user_roles, repository)
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
        
    @router.get(**routes_info['read'], response_model=dict)
    async def read_element(element_id: str, token: Annotated[str, Depends(oauth2_scheme)]):
        user_roles = await get_user_roles(repository, token, jwtSecretKey)
        _logger.info(user_roles)
        try:
            return await ReadLaiaBaseModel.read_laia_base_model(element_id, model, user_roles, repository)
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    @router.delete(**routes_info['delete'], response_model=str)
    async def delete_element(element_id: str, token: Annotated[str, Depends(oauth2_scheme)]):
        user_roles = await get_user_roles(repository, token, jwtSecretKey)
        _logger.info(user_roles)
        try:
            await DeleteLaiaBaseModel.delete_laia_base_model(element_id, model, user_roles, repository)
            return f"{model_name} element deleted successfully"
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    @router.post(**routes_info['search'], response_model=dict)
    async def search_element(token: Annotated[str, Depends(oauth2_scheme)], skip: int = 0, limit: int = 10, filters: dict = {}, orders: dict = {}):
        user_roles = await get_user_roles(repository, token, jwtSecretKey)
        _logger.info(user_roles)
        try:
            return await SearchLaiaBaseModel.search_laia_base_model(skip, limit, filters, orders, model, user_roles, repository)
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    return router

async def get_user_roles(repository: ModelRepository=None, token: Optional[str] = None, jwtSecretKey: str = 'secret_key') -> List[str]:
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing or invalid authorization header")

    try:
        payload = JWTToken.verify_jwt_token(token, jwtSecretKey)
        _logger.info(payload)
        
        user_roles_ids = payload.get("user_roles", [])
        _logger.info(user_roles_ids)
        user_roles = []
        for role in user_roles_ids:
            user_role = await ReadLaiaBaseModel.read_laia_base_model(role, Role, ['admin'], repository)
            user_roles.append(user_role['name'])

    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session token")
    
    return user_roles