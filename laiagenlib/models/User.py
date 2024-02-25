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
    roles: List[str] = []

    @classmethod
    async def create(cls, new_element: dict, model: Type, user_roles: list, crud_instance: CRUD):
        email = new_element.get('email')
        password = new_element.get('password')

        if not validate_email(email):
            raise ValueError("Invalid email address")
        
        if not validate_password(password):
            raise ValueError("Invalid password")
        
        existing_users, _ = await crud_instance.get_items(model_name=model.__name__.lower(), filters={'email': email})
        if existing_users:
            raise ValueError("User with this email already exists")
        
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

        user = await super().create({**new_element, 'password': hashed_password}, model, user_roles, crud_instance)
        return user
    
    @classmethod
    async def update(cls, element_id:str, updated_values: dict, model: Type, user_roles: list, crud_instance: CRUD):
        if 'email' in updated_values:
            new_email = updated_values['email']
            if not validate_email(new_email):
                raise ValueError("Invalid email address")
            
            existing_users, _ = await crud_instance.get_items(model_name=model.__name__.lower(), filters={'email': new_email})
        if existing_users:
            raise ValueError("User with this email already exists")
        
        if 'password' in updated_values and not validate_password(updated_values['password']):
            hashed_password = bcrypt.hashpw(updated_values['password'].encode('utf-8'), bcrypt.gensalt())
            updated_values['password'] = hashed_password.decode('utf-8')

        user = await super().update(element_id, {**updated_values, 'password': hashed_password}, model, user_roles, crud_instance)
        return user
    
    @classmethod
    async def register(cls, new_user_data: Dict[str, Any], model: Type, user_roles: list, crud_instance: CRUD):
        email = new_user_data.get('email')
        password = new_user_data.get('password')
        
        if not email or not password:
            raise ValueError("Email and password are required for registration")

        if not validate_email(email):
            raise ValueError("Invalid email address")
            
        if not validate_password(password):
            raise ValueError("Invalid password")
        
        existing_users, _ = await crud_instance.get_items(model_name=model.__name__.lower(), filters={'email': email})
        if existing_users:
            raise ValueError("User with this email already exists")

        user = await cls.create({**new_user_data}, model, user_roles, crud_instance)
        
        return user

    @classmethod
    async def login(cls, new_user_data: Dict[str, Any], model: Type, crud_instance: CRUD):
        email = new_user_data.get('email')
        password = new_user_data.get('password')

        if not email or not password:
            raise ValueError("Email and password are required for login")

        users, _ = await crud_instance.get_items(model_name=model.__name__.lower(), filters={'email': email})
        if not users:
            raise ValueError("User not found")
        
        user = users[0]

        if bcrypt.checkpw(password.encode('utf-8'), user.get('password').encode('utf-8')):
            return user
        else:
            raise ValueError("Incorrect email or password")