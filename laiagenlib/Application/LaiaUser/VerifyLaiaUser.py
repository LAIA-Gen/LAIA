from typing import Dict, Any

from fastapi import HTTPException, status
import bcrypt
from .JWTToken import create_jwt_token, verify_jwt_token
from ...Domain.LaiaBaseModel.ModelRepository import ModelRepository
from ...Domain.LaiaUser.LaiaUser import LaiaUser
from ...Domain.Shared.Utils.logger import _logger

async def verify(token: str, model: LaiaUser, repository: ModelRepository, jwtSecretKey: str):
    _logger.info("Verifying User")

    payload = verify_jwt_token(token, jwtSecretKey)
    user_id = payload.get("user_id")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing user_id"
        )

    user = await repository.get_item(
        model_name=model.__name__.lower(),
        item_id=user_id
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{model.__name__} not found"
        )

    if not user.get("validated", False):
        await repository.put_item(
            model_name=model.__name__.lower(),
            item_id=user_id,
            update_fields={"validated": True}
        )
        _logger.info("User validated")
    else:
        _logger.info("User was already validated")

    return {
        "valid": True,
        "message": f"{model.__name__} validated",
        "user_id": user_id
    }

