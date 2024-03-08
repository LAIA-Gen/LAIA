from typing import Dict, Type
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException
from ...Application.AccessRights.CreateAccessRights import create_access_rights
from ...Domain.AccessRights.AccessRights import AccessRight
from ...Domain.LaiaBaseModel.ModelRepository import ModelRepository
from ...Domain.Shared.Utils.logger import _logger

def create_access_rights_router(models: Dict[str, Type[BaseModel]], repository: ModelRepository) -> APIRouter:
    router = APIRouter(tags=["AccessRight"])

    @router.post("/create_access_rights/{model_name}")
    async def create_access_rights_route(model_name: str, new_access_rights: AccessRight):
        user_roles=["admin"]
        model = models.get(model_name)
        if not model:
            raise HTTPException(status_code=404, detail="Model not found")
        return await create_access_rights(new_access_rights, model, user_roles, repository)

    return router