import bcrypt
from typing import Type, Optional

from ..Shared.Utils import ValidatePassword
from ...Domain.LaiaBaseModel.ModelRepository import ModelRepository
from ...Domain.LaiaUser.LaiaUser import LaiaUser
from ...Domain.Shared.Utils.logger import _logger


async def change_password(
    user_id: str,
    new_password: str,
    model: Type,
    repository: ModelRepository,
    current_password: Optional[str] = None,
    require_current_password: bool = True,
):
    """
    Change the password for a user.

    - If require_current_password is True (non-admin), verifies the current password first.
    - If require_current_password is False (admin), skips current password verification.
    - Validates the new password meets minimum requirements.
    - Hashes the new password with bcrypt and updates it in the repository.
    """
    _logger.info(f"Changing password for user {user_id}")

    model_name = model.__name__.lower()

    # Fetch the user
    try:
        user_item = await repository.get_item(model_name, user_id)
    except ValueError:
        raise ValueError(f"User with ID {user_id} not found")

    # Verify current password if required (non-admin users)
    if require_current_password:
        if not current_password:
            raise ValueError("Current password is required")

        stored_password = user_item.get("password")
        if not stored_password:
            raise ValueError("User has no password set")

        if isinstance(stored_password, str):
            stored_password = stored_password.encode("utf-8")

        if not bcrypt.checkpw(current_password.encode("utf-8"), stored_password):
            raise PermissionError("Current password is incorrect")

    # Validate new password
    if not ValidatePassword.validate_password(new_password):
        raise ValueError("New password must be at least 8 characters long")

    # Hash and update
    hashed_password = bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt())

    await repository.put_item(model_name, user_id, {"password": hashed_password.decode("utf-8")})

    _logger.info(f"Password changed successfully for user {user_id}")
