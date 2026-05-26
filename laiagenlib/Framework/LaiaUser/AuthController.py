from fastapi import HTTPException, status, Body, Depends
from fastapi.routing import APIRouter
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import TypeVar, Optional, List
from pydantic import BaseModel

from laiagenlib.Application.LaiaUser import VerifyLaiaUser
from laiagenlib.Framework.Shared.ErrorMapping import handle_exception
from ...Application.LaiaUser import RegisterLaiaUser, LoginLaiaUser, JWTToken
from ...Application.LaiaUser.ChangePasswordLaiaUser import change_password
from ...Domain.LaiaUser.LaiaUser import LaiaUser
from ...Domain.LaiaUser.Auth import Auth
from ...Domain.LaiaBaseModel.ModelRepository import ModelRepository
from ...Domain.LaiaBaseModel import ReadLaiaBaseModel
from ...Domain.LaiaUser.Role import Role

from ...Domain.Shared.Utils.logger import _logger
from bson import ObjectId

T = TypeVar('T', bound='LaiaUser')
#JMT
def AuthController(repository: ModelRepository=None, model: T=None, jwtSecretKey: str='secret_key', jwtRefreshSecretKey: str='secret_refresh', smtp_config: dict = None, auth_required: bool = False):
    model_name = model.__name__.lower()
    router = APIRouter(tags=[model.__name__])
    http_bearer = HTTPBearer(auto_error=False)

    def get_token(credentials: Optional[HTTPAuthorizationCredentials] = Depends(http_bearer)) -> Optional[str]:
        return credentials.credentials if credentials else None

    def get_auth_dependency():
        if auth_required:
            return Optional[str]
        else:
            return Optional[str]

    async def get_user_roles(token: Optional[str] = None) -> List[str]:
        if not token:
            if auth_required:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing or invalid authorization header")
            else:
                return ["admin"]
        try:
            payload = JWTToken.verify_jwt_token(token, jwtSecretKey)
            user_roles_ids = payload.get("user_roles", [])
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

    async def get_user_id(token: Optional[str] = None):
        if not token:
            if auth_required:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing or invalid authorization header")
            return None
        try:
            payload = JWTToken.verify_jwt_token(token, jwtSecretKey)
            return payload.get("user_id")
        except ValueError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session token")

    class LoginResponse(BaseModel):
        user: model
        token: str
        refresh_token: str

    class VerifyResponse(BaseModel):
        valid: bool
        message: str
        user_id: str

    class RefreshResponse(BaseModel):
        token: str
        refresh_token: str

    class ErrorResponse(BaseModel):
        detail: str

    @router.post(f"/auth/register/{model_name}/", response_model=None, responses={200: {"model": model}, 400: {"model": ErrorResponse}, 409: {"model": ErrorResponse}})
    async def register_user(element: model):
        user_roles=["admin"]
        try:
            return await RegisterLaiaUser.register(dict(element), model, user_roles, repository, smtp_config)
        except ValueError as e:
            if "already exists" in str(e):
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except Exception as e:
            handle_exception(e)

    @router.post(f"/auth/login/{model_name}/", response_model=None, responses={200: {"model": LoginResponse}, 401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}})
    async def login_user(element: Auth):
        try:
            return await LoginLaiaUser.login(dict(element), model, repository, jwtSecretKey, jwtRefreshSecretKey)
        except ValueError as e:
            if str(e) == "User not found":
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
        except Exception as e:
            handle_exception(e)

    @router.get(f"/auth/verify/{model_name}/{{token}}", response_model=None, responses={200: {"model": VerifyResponse}, 401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}})
    async def verify_user(token: str):
        try:
            return await VerifyLaiaUser.verify(token, model, repository, jwtSecretKey)
        except HTTPException as e:
            raise e
        except Exception as e:
            handle_exception(e)
        
    @router.post(f"/auth/refresh/{model_name}/", response_model=None, responses={200: {"model": RefreshResponse}})
    async def refresh_token_route(refresh_token: str = Body(..., embed=True)):
        try:
            return JWTToken.refresh_token(refresh_token, jwtSecretKey, jwtRefreshSecretKey)
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))

    class ChangePasswordRequest(BaseModel):
        current_password: Optional[str] = None
        new_password: str
        user_id: Optional[str] = None

    class ChangePasswordResponse(BaseModel):
        message: str

    class ErrorResponse(BaseModel):
        detail: str

    @router.put(f"/auth/change-password/{model_name}/", response_model=None, responses={200: {"model": ChangePasswordResponse}, 400: {"model": ErrorResponse}, 401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}})
    async def change_password_route(body: ChangePasswordRequest, credentials: Optional[HTTPAuthorizationCredentials] = Depends(http_bearer)):
        """
        Cambiar la contraseña de un usuario.
        - Admin: puede cambiar la contraseña de cualquier usuario pasando user_id, sin necesidad de current_password.
        - Usuario normal: solo puede cambiar su propia contraseña, requiere current_password.
        """
        token = credentials.credentials if credentials else None
        if not token:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")

        user_roles = await get_user_roles(token)
        authenticated_user_id = await get_user_id(token)

        is_admin = "admin" in user_roles

        if body.user_id and not is_admin:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admins can change other users' passwords")

        target_user_id = body.user_id if body.user_id else authenticated_user_id

        if not target_user_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Could not determine user ID")

        require_current_password = not is_admin

        try:
            await change_password(
                user_id=target_user_id,
                new_password=body.new_password,
                current_password=body.current_password,
                model=model,
                repository=repository,
                require_current_password=require_current_password
            )
            return {"message": "Password changed successfully"}
        except Exception as e:
            handle_exception(e)

    return router