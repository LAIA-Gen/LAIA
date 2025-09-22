import bcrypt
from bson import ObjectId
from ..Shared.Utils import ValidateEmail, ValidatePassword
from ..LaiaBaseModel.UpdateLaiaBaseModel import update_laia_base_model
from ...Domain.LaiaBaseModel.ModelRepository import ModelRepository
from ...Domain.LaiaUser.LaiaUser import LaiaUser
from ...Domain.Shared.Utils.logger import _logger

async def update_laia_user(element_id:str, updated_values: dict, model: LaiaUser, user_roles: list, crud_instance: ModelRepository):
    _logger.info("Updating new User")

    if hasattr(updated_values, "dict"): 
        updated_values = updated_values.dict(exclude_unset=True)
    elif hasattr(updated_values, "model_dump"):
        updated_values = updated_values.model_dump(exclude_unset=True)
    elif not isinstance(updated_values, dict):
        updated_values = dict(updated_values)

    if 'email' in updated_values:
        new_email = updated_values['email']
        if not ValidateEmail.validate_email(new_email):
            raise ValueError("Invalid email address")
    
    if 'password' in updated_values:
        if not updated_values['password'].startswith('$2b$'):
            if not ValidatePassword.validate_password(updated_values['password']):
                raise ValueError("Invalid password")
            hashed_password = bcrypt.hashpw(updated_values['password'].encode('utf-8'), bcrypt.gensalt())
            updated_values['password'] = hashed_password.decode('utf-8')

    user = await update_laia_base_model(element_id, {**updated_values}, model, user_roles, crud_instance, True)
    _logger.info("User updated successfully")
    return user