from typing import Dict
from pydantic import BaseModel
from argapilib.crud import CRUD
from argapilib.logger import _logger
from argapilib.models.Model import create_element

class Role(BaseModel):
    name: str

    @classmethod
    async def create(cls, new_role, user_roles, crud_instance):
        role = Role(**new_role)
        if "admin" not in user_roles:
            raise PermissionError("Only users with 'admin' role can create new roles")

        existing_roles, _ = await crud_instance.get_items("role", skip=0, limit=10, filters={"name": role.name})
        if existing_roles:
            raise ValueError(f"Role with name '{role.name}' already exists")
        
        created_role = await create_element(role, crud_instance)
        return cls(**created_role)
