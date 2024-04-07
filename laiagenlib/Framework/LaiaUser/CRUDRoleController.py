from fastapi import HTTPException, status
from fastapi.routing import APIRouter
from typing import TypeVar
from ...Application.LaiaBaseModel import ReadLaiaBaseModel, DeleteLaiaBaseModel, SearchLaiaBaseModel, UpdateLaiaBaseModel
from ...Application.LaiaUser import CreateRole
from ...Domain.LaiaUser.Role import Role
from ...Domain.LaiaBaseModel.LaiaBaseModel import LaiaBaseModel
from ...Domain.LaiaBaseModel.ModelRepository import ModelRepository

T = TypeVar('T', bound='LaiaBaseModel')

async def CRUDRoleController(repository: ModelRepository=None):
    model = Role
    router = APIRouter(tags=[model.__name__])

    admin_role, _ = await repository.get_items("role", skip=0, limit=10, filters={ "name": "admin"})
    if not admin_role:
        await CreateRole.create_role({"name": "admin"}, ["admin"], repository)

    @router.post("/role/", response_model=dict)
    async def create_element(element: Role):
        user_roles=["admin"]
        try:
            return await CreateRole.create_role(dict(element), user_roles, repository)
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    @router.put("/role/{element_id}", response_model=dict)
    async def update_element(element_id: str, values: dict):
        user_roles=["admin"]
        try:
            return await UpdateLaiaBaseModel.update_laia_base_model(element_id, values, model, user_roles, repository)
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
        
    @router.get("/role/{element_id}", response_model=dict)
    async def read_element(element_id: str):
        user_roles=["admin"]
        try:
            return await ReadLaiaBaseModel.read_laia_base_model(element_id, model, user_roles, repository)
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    @router.delete("/role/{element_id}", response_model=str)
    async def delete_element(element_id: str):
        user_roles=["admin"]
        try:
            await DeleteLaiaBaseModel.delete_laia_base_model(element_id, model, user_roles, repository)
            return f"Role deleted successfully"
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    @router.post("/roles/", response_model=dict)
    async def search_element(skip: int = 0, limit: int = 10, filters: dict = {}, orders: dict = {}):
        user_roles=["admin"]
        try:
            return await SearchLaiaBaseModel.search_laia_base_model(skip, limit, filters, orders, model, user_roles, repository)
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    return router