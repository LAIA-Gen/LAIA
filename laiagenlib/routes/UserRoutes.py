from fastapi import FastAPI, HTTPException, status
from fastapi.routing import APIRouter
from typing import TypeVar
from ..crud.crud import CRUD
from ..models.User import LaiaUser
from pydantic import BaseModel

T = TypeVar('T', bound='LaiaUser')

class Auth(BaseModel):
    email: str
    password: str

def AuthRoutes(api: FastAPI, crud_instance: CRUD=None, model: T=None):
    model_name = model.__name__.lower()
    router = APIRouter(tags=[model.__name__])

    @router.post(f"/auth/register/{model_name}/", response_model=dict)
    async def register_user(element: model):
        user_roles=["admin"]
        try:
            return await model.register(dict(element), model, user_roles, crud_instance)
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    @router.post(f"/auth/login/{model_name}/", response_model=dict)
    async def login_user(element: Auth):
        user_roles=["admin"]
        try:
            return await model.login(dict(element), model, crud_instance)
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    api.include_router(router)