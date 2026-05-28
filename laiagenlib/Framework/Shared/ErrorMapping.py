from fastapi import HTTPException, status
from bson.errors import InvalidId


def handle_exception(e: Exception):
    """
    Maps Application-layer exceptions to proper HTTP status codes.

    - HTTPException → re-raised as-is (already has correct status code)
    - InvalidId → 500 with descriptive message about the invalid ObjectId
    - PermissionError → 403 Forbidden
    - ValueError → 404 if "not found"/"does not exist", 403 if permission-related, else 400
    - Everything else → 500 Internal Server Error
    """
    if isinstance(e, HTTPException):
        raise e

    if isinstance(e, InvalidId):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"bson.errors.InvalidId: {str(e)}"
        )

    if isinstance(e, PermissionError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )

    if isinstance(e, ValueError):
        msg = str(e).lower()
        if "not found" in msg or "does not exist" in msg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e)
            )
        if "permiso" in msg or "permission" in msg or "no tienes" in msg:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(e)
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=str(e)
    )
