from enum import Enum
from typing import Type

from laiagenlib.Application.LaiaBaseModel.SearchLaiaBaseModel import serialize_bson
from laiagenlib.Application.Shared.Utils.Slugify import ensure_unique_nicename, slugify
from ..AccessRights.CheckAccessRightsOfUser import check_access_rights_of_user
from ..AccessRights.CheckAccessRightsOfFields import check_access_rights_of_fields
from ..AccessRights.GetAllowedFields import get_allowed_fields
from ...Domain.LaiaBaseModel.ModelRepository import ModelRepository
from ...Domain.Shared.Utils.logger import _logger
from bson import ObjectId

async def create_laia_base_model(new_element: Type, model: Type, user_roles: list, repository: ModelRepository, use_access_rights: bool):
    _logger.info(f"Creating new {model.__name__} with values: {new_element}")
    
    model_name = model.__name__.lower()

    config = getattr(model, "model_config", {})
    extra = config.get("json_schema_extra", {})
    x_nicename = extra.get("x-nicename", False)
    default_fields = extra.get("x-frontend-defaultFields", [])
    first_field = default_fields[0] if default_fields else None

    if "admin" not in user_roles and use_access_rights:
        access_rights_list = await check_access_rights_of_user(model_name, user_roles, "create", repository)
        _logger.info(new_element)
        await check_access_rights_of_fields(model, 'fields_create', new_element, access_rights_list)

    if isinstance(new_element, dict):
        clean_element = {k: (v.value if isinstance(v, Enum) else v) for k, v in new_element.items()}
    else:
        clean_element = new_element.dict()
        clean_element = {k: (v.value if isinstance(v, Enum) else v) for k, v in clean_element.items()}

    if x_nicename and first_field and first_field in clean_element:
        raw_nicename = slugify(clean_element[first_field])
        clean_element['nicename'] = await ensure_unique_nicename(raw_nicename, model_name, repository)

    created_element = await repository.post_item(model_name, clean_element)

    if "admin" not in user_roles and use_access_rights:
        allowed_fields = get_allowed_fields(access_rights_list, 'fields_visible')
        _logger.info(allowed_fields)
        created_element = {field: created_element[field] for field in allowed_fields if field in created_element}

    _logger.info(f"{model.__name__} created successfully")
    return serialize_bson(created_element)