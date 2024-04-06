import jwt
from datetime import datetime, timedelta

def create_jwt_token(user_id: str, user_name: str, user_roles: list, jwtSecretKey: str) -> str:
    """
    Create a JWT token for the given user ID, name, and roles.
    """
    payload = {
        'user_id': user_id,
        'user_name': user_name,
        'user_roles': user_roles,
        'exp': datetime.utcnow() + timedelta(days=1) 
    }
    token = jwt.encode(payload, jwtSecretKey, algorithm='HS256')
    return token

def verify_jwt_token(token: str, jwtSecretKey: str) -> dict:
    """
    Verify the JWT token and return the payload if valid.
    """
    try:
        payload = jwt.decode(token, jwtSecretKey, algorithms=['HS256'])
        return payload
    except Exception:
        raise ValueError("Invalid session token")