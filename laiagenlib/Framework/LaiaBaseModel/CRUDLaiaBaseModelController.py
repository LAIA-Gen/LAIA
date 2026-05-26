from fastapi import Body, Depends, HTTPException, status
from laiagenlib.Framework.Shared.ErrorMapping import handle_exception
from fastapi.routing import APIRouter
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import TypeVar, Optional, List, Annotated, Any
from pydantic import BaseModel, Field

from laiagenlib.Application.Shared.Utils.UserShard import get_user_shard

from ...Application.LaiaBaseModel import ReadLaiaBaseModel, CreateLaiaBaseModel, DeleteLaiaBaseModel, SearchLaiaBaseModel, UpdateLaiaBaseModel, AggregateLaiaBaseModel
from ...Application.LaiaUser import JWTToken
from ...Application.Shared.Utils.StripExcludedFields import strip_excluded_fields
from ...Domain.LaiaBaseModel.LaiaBaseModel import LaiaBaseModel
from ...Domain.LaiaUser.Role import Role
from ...Domain.LaiaBaseModel.ModelRepository import ModelRepository
from ...Domain.Shared.Utils.logger import _logger
from bson import ObjectId
from laiagenlib.Domain.Shared.Utils.SerializeBson import serialize_bson


T = TypeVar('T', bound='LaiaBaseModel')
#JMT
def CRUDLaiaBaseModelController(repository: ModelRepository=None, model: T=None, update_model: T=None, routes_info: dict=None, jwtSecretKey: str='secret_key', auth_required: bool = False, use_access_rights: bool = True, use_ontology: bool = False, smtp_config: dict = None):
    model_name = model.__name__.lower()
    router = APIRouter(tags=[model.__name__])
    http_bearer = HTTPBearer(auto_error=False)

    def get_token(credentials: Optional[HTTPAuthorizationCredentials] = Depends(http_bearer)) -> Optional[str]:
        return credentials.credentials if credentials else None

    def is_public_operation(model, operation: str) -> bool:
        extra = getattr(model, "model_config", {}).get("json_schema_extra", {})
        _logger.info(f"is_public_operation: model={model.__name__}, extra={extra}")
        permissions = extra.get("x-permissions", {}) if isinstance(extra, dict) else {}
        _logger.info(f"is_public_operation: permissions={permissions}")
        if not permissions or not isinstance(permissions, dict):
            return False
        val = permissions.get(operation)
        _logger.info(f"is_public_operation: val for {operation}={val}")
        return val == []

    class SearchResponse(BaseModel):
        items: List[model]
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
        
    async def get_user_roles(repository: ModelRepository=None, token: Optional[str] = None, jwtSecretKey: str = 'secret_key', is_public: bool = False) -> List[str]:
        if not token:
            if auth_required and not is_public:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing or invalid authorization header")
            else:
                return ["admin"] if not auth_required else []

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
    
    async def get_user_id(repository: ModelRepository=None, token: Optional[str] = None, jwtSecretKey: str = 'secret_key', is_public: bool = False) -> Any:
        if not token:
            if auth_required and not is_public:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing or invalid authorization header")
            else:
                return ["admin"] if not auth_required else None

        try:
            payload = JWTToken.verify_jwt_token(token, jwtSecretKey)
            user_id = payload.get("user_id", [])

        except ValueError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session token")
        
        return ObjectId(user_id)

    @router.post(**routes_info['create'], response_model=None, responses={200: {"model": model}, 400: {"model": ErrorResponse}, 401: {"model": ErrorResponse}})
    async def create_element(element: model, token: get_auth_dependency() = None):
        is_public = is_public_operation(model, "create")
        user_roles = await get_user_roles(repository, token, jwtSecretKey, is_public)
        element_dict = element.dict()
        if auth_required:
            element_dict["owner"] = await get_user_id(repository, token, jwtSecretKey, is_public)

        element_full = model(**element_dict)
        user_shard = await get_user_shard(token, jwtSecretKey)

        try:
            return await CreateLaiaBaseModel.create_laia_base_model(element_full, model, user_roles, repository, use_access_rights, user_shard, smtp_config)
        except Exception as e:
            handle_exception(e)

    @router.put(**routes_info['update'], response_model=None, responses={200: {"model": model}, 401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}})
    async def update_element(element_id: str, values: update_model, token: get_auth_dependency() = None):
        is_public = is_public_operation(model, "update")
        user_roles = await get_user_roles(repository, token, jwtSecretKey, is_public)
        user_shard = await get_user_shard(token, jwtSecretKey)
        try:
            return await UpdateLaiaBaseModel.update_laia_base_model(element_id, values, model, user_roles, repository, use_access_rights, user_shard)
        except Exception as e:
            handle_exception(e)
        
    @router.get(**routes_info['read'], response_model=None, responses={200: {"model": model}, 401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}})
    async def read_element(element_id: str, token: get_auth_dependency() = None):
        is_public = is_public_operation(model, "read")
        user_roles = await get_user_roles(repository, token, jwtSecretKey, is_public)
        user_shard = await get_user_shard(token, jwtSecretKey)
        try:
            return await ReadLaiaBaseModel.read_laia_base_model(element_id, model, user_roles, repository, use_access_rights, user_shard)
        except Exception as e:
            handle_exception(e)

    @router.delete(**routes_info['delete'], response_model=str)
    async def delete_element(element_id: str, token: get_auth_dependency() = None):
        is_public = is_public_operation(model, "delete")
        user_roles = await get_user_roles(repository, token, jwtSecretKey, is_public)
        user_shard = await get_user_shard(token, jwtSecretKey)
        try:
            await DeleteLaiaBaseModel.delete_laia_base_model(element_id, model, user_roles, repository, use_access_rights, user_shard)
            return f"{model_name} element deleted successfully"
        except Exception as e:
            handle_exception(e)
    @router.post(**routes_info['search'], response_model=None, responses={200: {"model": SearchResponse}, 401: {"model": ErrorResponse}})
    async def search_element(token: get_auth_dependency() = None, skip: int = 0, limit: int = 10, filters: dict = Body({}), orders: dict = Body({}), populate: Optional[List] = Body(None)):
        is_public = is_public_operation(model, "search")
        user_roles = await get_user_roles(repository, token, jwtSecretKey, is_public)
        user_id = ''
        if auth_required:
            user_id = await get_user_id(repository, token, jwtSecretKey, is_public)
        user_shard = await get_user_shard(token, jwtSecretKey)
        try:
            return await SearchLaiaBaseModel.search_laia_base_model(skip, limit, filters, orders, model, user_roles, repository, user_id, use_access_rights, use_ontology, user_shard, populate=populate)
        except Exception as e:
            handle_exception(e)
        
    @router.get(**routes_info['nice'], response_model=None, responses={200: {"model": model}, 404: {"model": ErrorResponse}}, name=f"Get {model_name} by nicename")
    async def read_element_by_nicename(nicename: str, token: get_auth_dependency() = None):
        """
        Devuelve un {model_name} a partir del nicename
        """
        is_public = is_public_operation(model, "nice")
        user_roles = await get_user_roles(repository, token, jwtSecretKey, is_public)
        user_shard = await get_user_shard(token, jwtSecretKey)

        try:
            filters = {"nicename": nicename}
            extra = getattr(model, "model_config", {}).get("json_schema_extra", {})
            if extra.get("x-shard") and "admin" not in user_roles:
                shard_key = extra.get("x-shard-key", "region")
                if not user_shard:
                    raise HTTPException(status_code=403, detail="El usuario no tiene shard asignada")
                filters[shard_key] = user_shard
            data = await repository.get_items(
                model_name,
                skip=0,
                limit=1,
                filters=filters
            )
            if isinstance(data, tuple):
                items = data[0]
            elif isinstance(data, dict) and "items" in data:
                items = data["items"]
            else:
                items = data

            if not items:
                raise HTTPException(status_code=404, detail=f"{model_name} with nicename '{nicename}' not found")

            element = items[0]

            return serialize_bson(strip_excluded_fields(model, element))

        except Exception as e:
            handle_exception(e)
        
    @router.post(**routes_info['aggregate'], response_model=List[dict])
    async def aggregate_users(
        pipeline: List[dict] = Body(..., description="Pipeline MongoDB aggregation"),
        token: get_auth_dependency() = None
    ):
        is_public = is_public_operation(model, "aggregate")
        user_roles = await get_user_roles(repository, token, jwtSecretKey, is_public)
        user_id = ''
        if auth_required:
            user_id = await get_user_id(repository, token, jwtSecretKey, is_public)

        user_shard = await get_user_shard(token, jwtSecretKey)
        try:
            return await AggregateLaiaBaseModel.aggregate_laia_base_model(pipeline, model, user_roles, repository, user_id, True, user_shard)
        except Exception as e:
            handle_exception(e)

    return router
