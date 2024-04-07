from typing import Type
from pydantic import BaseModel
from ...Domain.AccessRights.AccessRights import AccessRight
from ...Domain.LaiaBaseModel.ModelRepository import ModelRepository
from ...Domain.Shared.Utils.logger import _logger

async def update_access_rights(element_id:str, repository: ModelRepository, new_access_rights: dict, model: Type[BaseModel], user_roles: list):
    _logger.info(f"Updating AccessRight with values: {new_access_rights}")

    if "admin" not in user_roles:
        raise PermissionError("Only users with 'admin' role can update access rights")

    existing_access_rights, _ = await repository.get_items(
        "accessright",
        skip=0,
        limit=1,
        filters={"id": element_id}
    )

    if not existing_access_rights:
        raise ValueError("AccessRight with the provided ID does not exist")
    
    existing_access_rights = existing_access_rights[0]

    if existing_access_rights.get("model") != new_access_rights.get("model", existing_access_rights.get("model")) or existing_access_rights.get("role") != new_access_rights.get("role", existing_access_rights.get("role")):
        raise ValueError("Model and role cannot be changed during update")
    
    try:
        access_right = AccessRight(**new_access_rights)
    except ValueError as ve:
        raise ValueError(str(ve))
    
    try:
        updated_element = await repository.put_item("accessright", element_id, new_access_rights)
    except Exception:
        raise ValueError(f"{model.__name__} with ID does not exist, or the updating parameters have errors")
    
    _logger.info(f"AccessRight updated successfully")
    return updated_element