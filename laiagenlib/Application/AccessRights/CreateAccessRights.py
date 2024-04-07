from typing import Type
from pydantic import BaseModel
from ...Domain.AccessRights.AccessRights import AccessRight
from ...Domain.LaiaBaseModel.ModelRepository import ModelRepository
from ...Domain.Shared.Utils.logger import _logger

async def create_access_rights(repository: ModelRepository, new_access_rights: dict, model: Type[BaseModel], user_roles: list):
    _logger.info(f"Creating new AccessRight with values: {new_access_rights}")

    if 'role' in new_access_rights and 'model' in new_access_rights:
        pass
    else:
        raise ValueError("Missing required parameters")
    
    existing_roles, _ = await repository.get_items(
        "role", 
        skip=0, 
        limit=10, 
        filters={
            "id": new_access_rights.get("role"),
        }
    )

    if not existing_roles:
        raise ValueError("Provided role does not exist")
    
    if new_access_rights.get("model").lower() != model.__name__.lower():
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
            
    existing_access_rights, _ = await repository.get_items(
        "accessright", 
        skip=0, 
        limit=10, 
        filters={
            "model": new_access_rights.get("model"),
            "role": new_access_rights.get("role")
        }
    )

    if existing_access_rights:
        raise ValueError("AccessRight with the same role and model already exists")
    
    try:
        access_rights = AccessRight(**new_access_rights)
    except Exception:
        raise ValueError("Missing required parameters")

    created_accessrights = await repository.post_item(
        "accessright",
        access_rights.model_dump()
    )
    _logger.info("AccessRight created successfully")
    return created_accessrights