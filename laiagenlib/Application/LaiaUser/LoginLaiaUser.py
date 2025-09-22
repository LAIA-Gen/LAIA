from typing import Dict, Any
import bcrypt
from laiagenlib.Domain.Shared.Utils.SerializeBson import serialize_bson
from .JWTToken import create_jwt_token
from ...Domain.LaiaBaseModel.ModelRepository import ModelRepository
from ...Domain.LaiaUser.LaiaUser import LaiaUser
from ...Domain.Shared.Utils.logger import _logger

async def login(new_user_data: Dict[str, Any], model: LaiaUser, repository: ModelRepository, jwtSecretKey: str, jwtRefreshSecretKey: str):
    _logger.info("Logging in User")
    email = new_user_data.get('email')
    password = new_user_data.get('password')

    if not email or not password:
        raise ValueError("Email and password are required for login")

    users, _ = await repository.get_items(model_name=model.__name__.lower(), filters={'email': email})
    if not users:
        raise ValueError("User not found")
    
    user = users[0]

    if bcrypt.checkpw(password.encode('utf-8'), user.get('password')):
        _logger.info("User logged in successfully")

        token_props = model.model_config.get("json_schema_extra", {}).get("x-token-properties", [])
        token_props = {prop: user.get(prop) for prop in token_props}

        tokens = create_jwt_token(user.get('id'), user.get('name'), user.get('roles'), jwtSecretKey, jwtRefreshSecretKey, token_props)

        return {
            'user': serialize_bson(user),
            'token': tokens['token'],
            'refresh_token': tokens['refresh_token']
        }
    else:
        raise ValueError("Incorrect email or password")