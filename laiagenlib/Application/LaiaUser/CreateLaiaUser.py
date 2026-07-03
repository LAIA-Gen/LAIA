import bcrypt
from typing import List
from ..Shared.Utils import ValidateEmail, ValidatePassword
from ..LaiaBaseModel.CreateLaiaBaseModel import create_laia_base_model
from ...Domain.LaiaBaseModel.ModelRepository import ModelRepository
from ...Domain.LaiaUser.LaiaUser import LaiaUser
from ...Domain.Shared.Utils.logger import _logger
from .ResolveRoles import resolve_role_ids

async def create_laia_user(new_element: dict, model: LaiaUser, user_roles: List[str], repository: ModelRepository, user_shard: str = "", smtp_config: dict = None):
    _logger.info("Creating new User")
    email = new_element.get('email')
    password = new_element.get('password')

    if 'roles' in new_element:
        new_element['roles'] = await resolve_role_ids(new_element['roles'], repository)
        
        admin_roles_db, _ = await repository.get_items("role", filters={"name": "admin"})
        if admin_roles_db:
            admin_role_id = admin_roles_db[0]['id']
            if admin_role_id in new_element['roles']:
                raise ValueError("No se puede asignar el rol de admin durante el registro")

    if not ValidateEmail.validate_email(email):
        raise ValueError("Invalid email address")
    
    if not ValidatePassword.validate_password(password):
        raise ValueError("Invalid password")
    
    existing_users, _ = await repository.get_items(model_name=model.__name__.lower(), filters={'email': email})
    if existing_users:
        raise ValueError("User with this email already exists")
    
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    
    user = await create_laia_base_model({**new_element, 'password': hashed_password}, model, user_roles, repository, True, user_shard, smtp_config=smtp_config)
    _logger.info("User created successfully")
    return user