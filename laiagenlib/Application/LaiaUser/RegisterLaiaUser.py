from typing import Type, Dict, Any
from .CreateLaiaUser import create_laia_user
from ..Shared.Utils import ValidateEmail, ValidatePassword
from ...Domain.LaiaBaseModel.ModelRepository import ModelRepository
from ...Domain.Shared.Utils.logger import _logger

async def register(new_user_data: Dict[str, Any], model: Type, user_roles: list, repository: ModelRepository):
    _logger.info("Registering new User")
    email = new_user_data.get('email')
    password = new_user_data.get('password')
    
    if not email or not password:
        raise ValueError("Email and password are required for registration")

    if not ValidateEmail.validate_email(email):
        raise ValueError("Invalid email address")
        
    if not ValidatePassword.validate_password(password):
        raise ValueError("Invalid password")
    
    existing_users, _ = await repository.get_items(model_name=model.__name__.lower(), filters={'email': email})
    if existing_users:
        raise ValueError("User with this email already exists")

    user = await create_laia_user({**new_user_data}, model, user_roles, repository)
    _logger.info("User registered successfully")
    return user