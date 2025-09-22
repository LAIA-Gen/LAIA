import jwt
from datetime import datetime, timedelta

def create_jwt_token(user_id: str, user_name: str, user_roles: list, jwtSecretKey: str, jwtRefreshSecretKey: str, token_props: dict) -> dict:
    """
    Create both an access token and a refresh token for the user.
    Access token lasts 5 minutes.
    Refresh token lasts 7 days.
    """
    base_payload = {
        "user_id": user_id,
        "user_name": user_name,
        "user_roles": user_roles,
    }

    access_payload = {
        **base_payload,
        **token_props,
        "type": "access",
        "exp": datetime.utcnow() + timedelta(minutes=5),
    }

    refresh_payload = {
        **base_payload,
        **token_props,
        "type": "refresh",
        "exp": datetime.utcnow() + timedelta(days=7),
    }

    access_token = jwt.encode(access_payload, jwtSecretKey, algorithm='HS256')
    refresh_token = jwt.encode(refresh_payload, jwtRefreshSecretKey, algorithm='HS256')

    return {
        "token": access_token,
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
    
def refresh_token(refresh_token: str, jwtSecretKey: str, jwtRefreshSecretKey: str) -> dict:
    """
    Validate the refresh token and return new access and refresh tokens.
    """
    try:
        payload = jwt.decode(refresh_token, jwtRefreshSecretKey, algorithms=["HS256"])

        if payload.get("type") != "refresh":
            raise Exception("Invalid token type")

        base_payload = {k: v for k, v in payload.items() if k not in ["type", "exp"]}

        new_access_payload = {
            **base_payload,
            "type": "access",
            "exp": datetime.utcnow() + timedelta(minutes=5),
        }

        new_refresh_payload = {
            **base_payload,
            "type": "refresh",
            "exp": datetime.utcnow() + timedelta(days=7),
        }

        new_access_token = jwt.encode(new_access_payload, jwtSecretKey, algorithm="HS256")
        new_refresh_token = jwt.encode(new_refresh_payload, jwtRefreshSecretKey, algorithm="HS256")

        return {
            "token": new_access_token,
            "refresh_token": new_refresh_token
        }

    except jwt.ExpiredSignatureError:
        raise Exception("Refresh token expired")
    except jwt.InvalidTokenError:
        raise Exception("Invalid refresh token")