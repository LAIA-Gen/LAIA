import bcrypt
from ..Shared.Utils import ValidateEmail, ValidatePassword
from ..LaiaBaseModel.UpdateLaiaBaseModel import update_laia_base_model
from ...Domain.LaiaBaseModel.ModelRepository import ModelRepository
from ...Domain.LaiaUser.LaiaUser import LaiaUser
from ...Domain.Shared.Utils.logger import _logger

async def update_laia_user(element_id:str, updated_values: dict, model: LaiaUser, user_roles: list, crud_instance: ModelRepository):
    _logger.info("Updating new User")
    if 'email' in updated_values:
        new_email = updated_values['email']
        if not ValidateEmail.validate_email(new_email):
            raise ValueError("Invalid email address")
    
    if 'password' in updated_values:
        if not ValidatePassword.validate_password(updated_values['password']):
            raise ValueError("Invalid password")
        hashed_password = bcrypt.hashpw(updated_values['password'].encode('utf-8'), bcrypt.gensalt())
        updated_values['password'] = hashed_password.decode('utf-8')

    user = await update_laia_base_model(element_id, {**updated_values, 'password': hashed_password}, model, user_roles, crud_instance)
    _logger.info("User updated successfully")
    return user