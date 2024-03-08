from typing import Type
from ..AccessRights.CheckAccessRightsOfUser import check_access_rights_of_user
from ..AccessRights.CheckAccessRightsOfFields import check_access_rights_of_fields
from ..AccessRights.GetAllowedFields import get_allowed_fields
from ...Domain.LaiaBaseModel.ModelRepository import ModelRepository
from ...Domain.Shared.Utils.logger import _logger

async def create_laia_base_model(new_element: dict, model: Type, user_roles: list, repository: ModelRepository):
    _logger.info(f"Creating new {model.__name__} with values: {new_element}")

    try:
        element = model(**new_element)
    except Exception:
        raise ValueError("Missing required parameters")
    
    model_name = model.__name__.lower()

    if "admin" not in user_roles:
        access_rights_list = await check_access_rights_of_user(model_name, user_roles, "create", repository)
        _logger.info("ACCESSSSS: " + str(access_rights_list))
        _logger.info(new_element)
        await check_access_rights_of_fields(model, 'fields_create', new_element, access_rights_list)
    
    created_element = await repository.post_item(
        model_name,
        element.model_dump()
    )

    if "admin" not in user_roles:
        allowed_fields = get_allowed_fields(access_rights_list, 'fields_visible')
        created_element = {field: created_element[field] for field in allowed_fields if field in created_element}

    _logger.info(f"{model.__name__} created successfully")
    return created_element