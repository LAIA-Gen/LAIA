from fastapi import HTTPException, status, Body
from fastapi.routing import APIRouter
from typing import TypeVar
from pydantic import BaseModel

from laiagenlib.Application.LaiaUser import VerifyLaiaUser
from ...Application.LaiaUser import RegisterLaiaUser, LoginLaiaUser, JWTToken
from ...Domain.LaiaUser.LaiaUser import LaiaUser
from ...Domain.LaiaUser.Auth import Auth
from ...Domain.LaiaBaseModel.ModelRepository import ModelRepository

from ...Domain.Shared.Utils.logger import _logger

T = TypeVar('T', bound='LaiaUser')
#JMT
def AuthController(repository: ModelRepository=None, model: T=None, jwtSecretKey: str='secret_key', jwtRefreshSecretKey: str='secret_refresh', smtp_config: dict = None):
    model_name = model.__name__.lower()
    router = APIRouter(tags=[model.__name__])

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

    @router.post(f"/auth/register/{model_name}/", response_model=model)
    async def register_user(element: model):
        user_roles=["admin"]
        try:
            return await RegisterLaiaUser.register(dict(element), model, user_roles, repository, smtp_config)
        except ValueError as e:
            if "already exists" in str(e):
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    @router.post(f"/auth/login/{model_name}/", response_model=LoginResponse)
    async def login_user(element: Auth):
        try:
            return await LoginLaiaUser.login(dict(element), model, repository, jwtSecretKey, jwtRefreshSecretKey)
        except ValueError as e:
            if str(e) == "User not found":
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    @router.get(f"/auth/verify/{model_name}/{{token}}", response_model=VerifyResponse)
    async def verify_user(token: str):
        try:
            return await VerifyLaiaUser.verify(token, model, repository, jwtSecretKey)
        except HTTPException as e:
            raise e
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
        
    @router.post(f"/auth/refresh/{model_name}/", response_model=RefreshResponse)
    async def refresh_token_route(refresh_token: str = Body(..., embed=True)):
        try:
            return JWTToken.refresh_token(refresh_token, jwtSecretKey, jwtRefreshSecretKey)
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))

    return router