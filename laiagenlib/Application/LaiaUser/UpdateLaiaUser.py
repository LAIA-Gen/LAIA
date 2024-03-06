from typing import Type
import bcrypt
from ..Shared.Utils import ValidateEmail, ValidatePassword
from ..LaiaBaseModel.UpdateLaiaBaseModel import update_laia_base_model
from ...Domain.LaiaBaseModel.ModelRepository import ModelRepository
from ...Domain.Shared.Utils.logger import _logger

async def update_laia_user(element_id:str, updated_values: dict, model: Type, user_roles: list, crud_instance: ModelRepository):
    _logger.info("Updating new User")
    if 'email' in updated_values:
        new_email = updated_values['email']
        if not ValidateEmail.validate_email(new_email):
            raise ValueError("Invalid email address")
        
        existing_users, _ = await crud_instance.get_items(model_name=model.__name__.lower(), filters={'email': new_email})
    if existing_users:
        raise ValueError("User with this email already exists")
    
    if 'password' in updated_values and not ValidatePassword.validate_password(updated_values['password']):
        hashed_password = bcrypt.hashpw(updated_values['password'].encode('utf-8'), bcrypt.gensalt())
        updated_values['password'] = hashed_password.decode('utf-8')

    user = await update_laia_base_model(element_id, {**updated_values, 'password': hashed_password}, model, user_roles, crud_instance)
    _logger.info("User updated successfully")
    return user