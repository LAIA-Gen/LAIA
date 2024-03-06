from typing import Type, List
from ..AccessRights.CheckAccessRightsOfUser import check_access_rights_of_user
from ..AccessRights.GetAllowedFields import get_allowed_fields
from ...Domain.LaiaBaseModel.ModelRepository import ModelRepository
from ...Domain.Shared.Utils.logger import _logger

async def read_laia_base_model(element_id: str, model: Type, user_roles: List[str], repository: ModelRepository):
    _logger.info(f"Getting {model.__name__} with ID: {element_id}")

    model_name = model.__name__.lower()

    if "admin" not in user_roles:
        access_rights_list = await check_access_rights_of_user(model_name, user_roles, "read", repository)
    try:
        item = await repository.get_item(model_name, element_id)
    except ValueError as e:
        raise ValueError(str(e))

    if "admin" not in user_roles:
        allowed_fields = get_allowed_fields(access_rights_list, 'fields_visible')
        item = {field: item[field] for field in allowed_fields if field in item}

    _logger.info(f"{model.__name__} retrieved successfully")
    return item