from typing import Type, List, Dict, Any
import bcrypt
from ..utils.utils import validate_email, validate_password
from ..crud.crud import CRUD
from .AccessRights import AccessRight
from .Model import LaiaBaseModel
from ..utils.logger import _logger

class LaiaUser(LaiaBaseModel):
    email: str = ""
    password: str

    @classmethod
    async def create(cls, new_element: dict, model: Type, user_roles: list, crud_instance: CRUD):
        if not validate_email(new_element['email']):
            raise ValueError("Invalid email address")
        
        if not validate_email(new_element['password']):
            raise ValueError("Invalid password")
        
        hashed_password = bcrypt.hashpw(new_element['password'].encode('utf-8'), bcrypt.gensalt())

        user = await super().create({**new_element, 'password': hashed_password}, model, user_roles, crud_instance)
        return user
    
    @classmethod
    async def update(cls, element_id:str, updated_values: dict, model: Type, user_roles: list, crud_instance: CRUD):
        if 'email' in updated_values and not validate_email(updated_values['email']):
            raise ValueError("Invalid email address")
        
        if 'password' in updated_values and not validate_password(updated_values['password']):
            hashed_password = bcrypt.hashpw(updated_values['password'].encode('utf-8'), bcrypt.gensalt())
            updated_values['password'] = hashed_password.decode('utf-8')

        user = await super().create(element_id, {**updated_values, 'password': hashed_password}, model, user_roles, crud_instance)
        return user