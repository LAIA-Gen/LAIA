from fastapi import FastAPI, HTTPException, status
from fastapi.routing import APIRouter
from typing import TypeVar
from ..crud.crud import CRUD
from ..models.Model import LaiaBaseModel

T = TypeVar('T', bound='LaiaBaseModel')

def ModelCRUD(api: FastAPI, crud_instance: CRUD=None, model: T=None, routes_info: dict=None):
    model_name = model.__name__.lower()
    router = APIRouter(tags=[model.__name__])

    @router.post(**routes_info['create'], response_model=dict)
    async def create_element(element: model):
        user_roles=["admin"]
        try:
            return await model.create(dict(element), model, user_roles, crud_instance)
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    @router.put(**routes_info['update'], response_model=dict)
    async def update_element(element_id: str, values: dict):
        user_roles=["admin"]
        try:
            return await model.update(element_id, values, model, user_roles, crud_instance)
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
        
    @router.get(**routes_info['read'], response_model=dict)
    async def read_element(element_id: str):
        user_roles=["admin"]
        try:
            return await model.read(element_id, model, user_roles, crud_instance)
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    @router.delete(**routes_info['delete'], response_model=str)
    async def delete_element(element_id: str):
        user_roles=["admin"]
        try:
            await model.delete(element_id, model, user_roles, crud_instance)
            return f"{model_name} element deleted successfully"
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    @router.post(**routes_info['search'], response_model=dict)
    async def search_element(skip: int = 0, limit: int = 10, filters: dict = {}, orders: dict = {}):
        user_roles=["admin"]
        try:
            return await model.search(skip, limit, filters, orders, model, user_roles, crud_instance)
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    api.include_router(router)