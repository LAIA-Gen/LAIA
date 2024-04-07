from typing import Dict, Type
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, status
from ...Application.LaiaBaseModel import ReadLaiaBaseModel, DeleteLaiaBaseModel, SearchLaiaBaseModel, UpdateLaiaBaseModel
from ...Application.AccessRights import CreateAccessRights, UpdateAccessRights
from ...Domain.AccessRights.AccessRights import AccessRight
from ...Domain.LaiaBaseModel.ModelRepository import ModelRepository
from ...Domain.Shared.Utils.logger import _logger

def CRUDAccessRightsController(models: Dict[str, Type[BaseModel]], repository: ModelRepository) -> APIRouter:
    model = AccessRight
    router = APIRouter(tags=["AccessRight"])

    @router.post("/accessright/")
    async def create_access_rights_route(new_access_rights: AccessRight):
        user_roles=["admin"]
        model = models.get(new_access_rights.model)
        if not model:
            raise HTTPException(status_code=404, detail="Model not found")
        try:
            return await CreateAccessRights.create_access_rights(repository, dict(new_access_rights), model, user_roles)
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    @router.put("/accessright/{element_id}", response_model=dict)
    async def update_access_rights(element_id: str, values: dict):
        user_roles=["admin"]
        try:
            return await UpdateAccessRights.update_access_rights(element_id, repository, values, model, user_roles)
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
        
    @router.get("/accessright/{element_id}", response_model=dict)
    async def read_access_rights(element_id: str):
        user_roles=["admin"]
        try:
            return await ReadLaiaBaseModel.read_laia_base_model(element_id, model, user_roles, repository)
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    @router.delete("/accessright/{element_id}", response_model=str)
    async def delete_access_rights(element_id: str):
        user_roles=["admin"]
        try:
            await DeleteLaiaBaseModel.delete_laia_base_model(element_id, model, user_roles, repository)
            return f"AccessRight deleted successfully"
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    @router.post("/accessrights/", response_model=dict)
    async def search_access_rights(skip: int = 0, limit: int = 10, filters: dict = {}, orders: dict = {}):
        user_roles=["admin"]
        try:
            return await SearchLaiaBaseModel.search_laia_base_model(skip, limit, filters, orders, model, user_roles, repository)
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    return router