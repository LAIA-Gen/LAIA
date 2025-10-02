from typing import Optional

from fastapi import HTTPException, status

from laiagenlib.Application.LaiaUser import JWTToken
from laiagenlib.Domain.Shared.Utils.logger import _logger


async def get_user_shard(token: Optional[str] = None, jwtSecretKey: str = 'secret_key') -> Optional[str]:
    _logger.error(token)
    if not token:
        return None
    try:
        payload = JWTToken.verify_jwt_token(token, jwtSecretKey)
        _logger.error(payload)
        return payload.get("shard")
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session token")