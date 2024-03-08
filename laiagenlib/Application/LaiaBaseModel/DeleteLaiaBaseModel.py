from typing import Type, List
from ..AccessRights.CheckAccessRightsOfUser import check_access_rights_of_user
from ...Domain.LaiaBaseModel.ModelRepository import ModelRepository
from ...Domain.Shared.Utils.logger import _logger

async def delete_laia_base_model(element_id: str, model: Type, user_roles: List[str], repository: ModelRepository):
    _logger.info(f"Deleting {model.__name__} with ID: {element_id}")

    model_name = model.__name__.lower()

    if "admin" not in user_roles:
        await check_access_rights_of_user(model_name, user_roles, "delete", repository)
    try:
        await repository.delete_item(model_name, element_id)
    except Exception:
        raise ValueError(f"{model.__name__} with ID does not exist, or there was an error deleting the element")

    _logger.info(f"{model.__name__} deleted successfully")