import jwt
from datetime import datetime, timedelta

def create_jwt_token(user_id: str, user_name: str, user_roles: list, jwtSecretKey: str) -> dict:
    """
    Create both an access token and a refresh token for the user.
    Access token lasts 5 minutes.
    Refresh token lasts 7 days.
    """
    access_payload = {
        'user_id': user_id,
        'user_name': user_name,
        'user_roles': user_roles,
        'type': 'access',
        'exp': datetime.utcnow() + timedelta(minutes=5)
    }

    refresh_payload = {
        'user_id': user_id,
        'user_name': user_name,
        'user_roles': user_roles,
        'type': 'refresh',
        'exp': datetime.utcnow() + timedelta(days=7)
    }

    access_token = jwt.encode(access_payload, jwtSecretKey, algorithm='HS256')
    refresh_token = jwt.encode(refresh_payload, jwtSecretKey, algorithm='HS256')

    return {
        "access_token": access_token,
        "refresh_token": refresh_token
    }

def verify_jwt_token(token: str, jwtSecretKey: str) -> dict:
    """
    Verify the JWT token and return the payload if valid.
    """
    try:
        payload = jwt.decode(token, jwtSecretKey, algorithms=['HS256'])
        return payload
    except Exception:
        raise ValueError("Invalid session token")