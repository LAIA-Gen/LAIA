from typing import Dict
from pydantic import BaseModel
from argapilib.crud import CRUD
from argapilib.logger import _logger
from argapilib.models.Role import Role
from argapilib.models.Model import Model, create_element

class AccessRights(BaseModel):
    role: Role
    model: Model
    operations: Dict[str, int]
    fields_create: Dict[str, int]
    fields_edit: Dict[str, int]
    fields_visible: Dict[str, int]

    @classmethod
    async def create(cls, new_access_rights, user_roles: list, crud_instance: CRUD):

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
            
            model_fields = [field.name for field in cls.model.__annotations__.values()]

            for field_name, field_value in fields.items():
                if field_name not in model_fields or not isinstance(field_value, int):
                    raise ValueError(f"Invalid field {field_name} for {field_type}")
                
        created_accessrights = await create_element(new_access_rights, crud_instance)
        return cls(**created_accessrights)
