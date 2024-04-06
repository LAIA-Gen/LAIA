from fastapi import HTTPException, status
from fastapi.routing import APIRouter
from typing import TypeVar
from ...Application.LaiaUser import RegisterLaiaUser, LoginLaiaUser, JWTToken
from ...Domain.LaiaUser.LaiaUser import LaiaUser
from ...Domain.LaiaUser.Auth import Auth
from ...Domain.LaiaBaseModel.ModelRepository import ModelRepository

T = TypeVar('T', bound='LaiaUser')

def AuthController(repository: ModelRepository=None, model: T=None, jwtSecretKey: str='secret_key'):
    model_name = model.__name__.lower()
    router = APIRouter(tags=[model.__name__])

    @router.post(f"/auth/register/{model_name}/", response_model=dict)
    async def register_user(element: model):
        user_roles=["admin"]
        try:
            return await RegisterLaiaUser.register(dict(element), model, user_roles, repository, jwtSecretKey)
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    @router.post(f"/auth/login/{model_name}/", response_model=dict)
    async def login_user(element: Auth):
        user_roles=["admin"]
        try:
            return await LoginLaiaUser.login(dict(element), model, repository, jwtSecretKey)
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    @router.get(f"/auth/verify/{model_name}/{{token}}", response_model=dict)
    async def verify_user(token: str):
        user_roles=["admin"]
        try:
            return JWTToken.verify_jwt_token(token, jwtSecretKey)
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    return router