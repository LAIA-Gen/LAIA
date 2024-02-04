from typing import Dict
from pydantic import BaseModel
from argapilib.crud import CRUD
from argapilib.logger import _logger
from argapilib.models.Model import create_element

class Role(BaseModel):
    name: str

    @classmethod
    async def create(cls, new_role: dict, user_roles: list, crud_instance: CRUD):
        _logger.info(f"Creating new Role with values: {new_role}")

        if "name" not in new_role:
            raise ValueError("Missing required parameter: name")

        role = Role(**new_role)
        if "admin" not in user_roles:
            raise PermissionError("Only users with 'admin' role can create new roles")

        existing_roles, _ = await crud_instance.get_items("role", skip=0, limit=10, filters={"name": role.name})
        if existing_roles:
            raise ValueError(f"Role with name '{role.name}' already exists")
        
        created_role = await create_element(role, crud_instance)
        _logger.info("Role created successfully")
        return cls(**created_role)
