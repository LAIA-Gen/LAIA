from fastapi import HTTPException, status
from fastapi.routing import APIRouter
from typing import TypeVar
from ...Application.LaiaBaseModel import ReadLaiaBaseModel, CreateLaiaBaseModel, DeleteLaiaBaseModel, SearchLaiaBaseModel, UpdateLaiaBaseModel
from ...Domain.LaiaBaseModel.LaiaBaseModel import LaiaBaseModel
from ...Domain.LaiaBaseModel.ModelRepository import ModelRepository

T = TypeVar('T', bound='LaiaBaseModel')

def CRUDLaiaBaseModelController(repository: ModelRepository=None, model: T=None, routes_info: dict=None):
    model_name = model.__name__.lower()
    router = APIRouter(tags=[model.__name__])

    @router.post(**routes_info['create'], response_model=dict)
    async def create_element(element: model):
        user_roles=["admin"]
        try:
            return await CreateLaiaBaseModel.create_laia_base_model(dict(element), model, user_roles, repository)
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    @router.put(**routes_info['update'], response_model=dict)
    async def update_element(element_id: str, values: dict):
        user_roles=["admin"]
        try:
            return await UpdateLaiaBaseModel.update_laia_base_model(element_id, values, model, user_roles, repository)
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
        
    @router.get(**routes_info['read'], response_model=dict)
    async def read_element(element_id: str):
        user_roles=["admin"]
        try:
            return await ReadLaiaBaseModel.read_laia_base_model(element_id, model, user_roles, repository)
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    @router.delete(**routes_info['delete'], response_model=str)
    async def delete_element(element_id: str):
        user_roles=["admin"]
        try:
            await DeleteLaiaBaseModel.delete_laia_base_model(element_id, model, user_roles, repository)
            return f"{model_name} element deleted successfully"
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    @router.post(**routes_info['search'], response_model=dict)
    async def search_element(skip: int = 0, limit: int = 10, filters: dict = {}, orders: dict = {}):
        user_roles=["admin"]
        try:
            return await SearchLaiaBaseModel.search_laia_base_model(skip, limit, filters, orders, model, user_roles, repository)
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    return router