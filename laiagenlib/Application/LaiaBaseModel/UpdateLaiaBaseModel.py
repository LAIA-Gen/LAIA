from typing import Type

from laiagenlib.Domain.Shared.Utils.SerializeBson import serialize_bson
from ..AccessRights.CheckAccessRightsOfUser import check_access_rights_of_user
from ..AccessRights.CheckAccessRightsOfFields import check_access_rights_of_fields
from ..AccessRights.GetAllowedFields import get_allowed_fields
from ...Domain.LaiaBaseModel.ModelRepository import ModelRepository
from ...Domain.Shared.Utils.logger import _logger
from fastapi.encoders import jsonable_encoder

async def update_laia_base_model(element_id:str, updated_values: dict, model: Type, user_roles: list, repository: ModelRepository):
    _logger.info(f"Updating {model.__name__} with ID: {element_id} and values: {updated_values}")

    if hasattr(updated_values, "model_dump"):            
        updated_values = updated_values.model_dump(exclude_unset=True)
    elif hasattr(updated_values, "dict"):               
        updated_values = updated_values.dict(exclude_unset=True)
    elif not isinstance(updated_values, dict):
        updated_values = dict(updated_values)

    updated_values = jsonable_encoder(updated_values, exclude_none=True)

    model_name = model.__name__.lower()

    if "admin" not in user_roles:
        access_rights_list = await check_access_rights_of_user(model_name, user_roles, "update", repository)
        await check_access_rights_of_fields(model, 'fields_edit', updated_values, access_rights_list)

    try:
        updated_element = await repository.put_item(model_name, element_id, updated_values)
    except KeyError as e:
        _logger.exception("Field error while updating %s: %s", model.__name__, e)
        raise ValueError(f"Invalid field(s) in update: {e}") from e
    except ValueError as e:
        _logger.exception("Value error while updating %s: %s", model.__name__, e)
        raise
    except Exception as e:
        _logger.exception("Unexpected error updating %s with ID %s", model.__name__, element_id)
        raise 
    
    if "admin" not in user_roles:
        allowed_fields = get_allowed_fields(access_rights_list, 'fields_visible')
        updated_element = {field: updated_element[field] for field in allowed_fields if field in updated_element}

    _logger.info(f"{model.__name__} updated successfully")
    return serialize_bson(updated_element)