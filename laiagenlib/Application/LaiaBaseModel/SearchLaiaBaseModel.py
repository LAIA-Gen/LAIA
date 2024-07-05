from typing import Type, List
from math import ceil
from ..AccessRights.CheckAccessRightsOfUser import check_access_rights_of_user
from ..AccessRights.GetAllowedFields import get_allowed_fields
from ...Domain.LaiaBaseModel.ModelRepository import ModelRepository
from ...Domain.Shared.Utils.logger import _logger

async def search_laia_base_model(skip: int, limit: int, filters: dict, orders: dict, model: Type, user_roles: List[str], repository: ModelRepository, user_id: str = ''):
    _logger.info(f"Searching {model.__name__} with filters: {filters}")

    model_name = model.__name__.lower()

    if "admin" not in user_roles:
        access_rights_list = await check_access_rights_of_user(model_name, user_roles, "search", repository)
        _logger.info("USER ID: " + user_id)
        _logger.info(access_rights_list)
        if not any(not access_right.owner for access_right in access_rights_list):
            _logger.info("HEY")
            filters["owner"] = user_id

    try:
        items, total_count = await repository.get_items(model_name, skip=skip, limit=limit, filters=filters, orders=orders)
        if "admin" not in user_roles:
            allowed_fields = get_allowed_fields(access_rights_list, 'fields_visible')
            items = [
                {field: item[field] for field in allowed_fields if field in item}
                for item in items
            ]
        max_pages = ceil(total_count / limit)
        current_page = (skip // limit) + 1
    except Exception:
        raise ValueError(f"Error occurred while searching {model.__name__} with filters: {filters}")

    _logger.info(f"{model.__name__} search completed successfully")
    return {
        "items": items,
        "current_page": current_page,
        "max_pages": max_pages,
    }