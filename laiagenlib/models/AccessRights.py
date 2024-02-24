from typing import Dict, Type
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from ..crud.crud import CRUD
from ..utils.logger import _logger
from ..utils.utils import create_element

class AccessRight(BaseModel):
    role: str
    model: str
    operations: Dict[str, int] = {}
    fields_create: Dict[str, int] = {}
    fields_edit: Dict[str, int] = {}
    fields_visible: Dict[str, int] = {}

def create_access_rights_router(router: APIRouter, models: Dict[str, Type[BaseModel]], crud_instance: CRUD) -> APIRouter:

    async def create_access_rights(new_access_rights: dict, model: Type[BaseModel], user_roles: list, crud_instance: CRUD):
        _logger.info(f"Creating new AccessRights with values: {new_access_rights}")

        if 'role' in new_access_rights and 'model' in new_access_rights:
            pass
        else:
            raise ValueError("Missing required parameters")

        if new_access_rights.get("model") != model.__name__.lower():
            raise ValueError("Provided model name does not match the class model name")

        if "admin" not in user_roles:
            raise PermissionError("Only users with 'admin' role can create access rights")
        
        operations = new_access_rights.get("operations", {})
        valid_operations = {"create", "read", "update", "delete", "search"}

        for operation in operations:
            if operation not in valid_operations or not isinstance(operations[operation], int):
                raise ValueError(f"Invalid format for operation {operation}")
            
        fields_to_check = ["fields_create", "fields_edit", "fields_visible"]

        for field_type in fields_to_check:
            fields = new_access_rights.get(field_type, {})
            if not isinstance(fields, dict):
                raise ValueError(f"Invalid format for {field_type}")
            
            model_fields = []
            for class_in_hierarchy in model.mro():
                if hasattr(class_in_hierarchy, '__annotations__'):
                    model_fields.extend([field for field in class_in_hierarchy.__annotations__ if not field.startswith("_")])

            for field_name, field_value in fields.items():
                if field_name not in model_fields or not isinstance(field_value, int):
                    raise ValueError(f"Invalid field {field_name} for {field_type}")
                
        existing_access_rights, _ = await crud_instance.get_items(
            "accessrights", 
            skip=0, 
            limit=10, 
            filters={
                "model": new_access_rights.get("model"),
                "role": new_access_rights.get("role")
            }
        )

        if existing_access_rights:
            raise ValueError("AccessRights with the same role and model already exists")
        
        try:
            access_rights = AccessRight(**new_access_rights)
        except Exception:
            raise ValueError("Missing required parameters")

        created_accessrights = await create_element(access_rights, crud_instance)
        _logger.info("AccessRights created successfully")
        return created_accessrights

    @router.post("/create_access_rights/{model_name}")
    async def create_access_rights_route(model_name: str, new_access_rights: dict):
        user_roles=["admin"]
        model = models.get(model_name)
        if not model:
            raise HTTPException(status_code=404, detail="Model not found")
        return await create_access_rights(new_access_rights, model, user_roles, crud_instance)

    return router