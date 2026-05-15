from typing import Type

from bson import ObjectId

from .UpdateLaiaBaseModel import convert_objectid_fields
from ..AccessRights.CheckAccessRightsOfUser import check_access_rights_of_user
from ..AccessRights.CheckAccessRightsOfFields import check_access_rights_of_fields
from ..AccessRights.GetAllowedFields import get_allowed_fields
from ...Domain.LaiaBaseModel.ModelRepository import ModelRepository
from ...Domain.Shared.Utils.logger import _logger
from laiagenlib.Domain.Shared.Utils.SerializeBson import serialize_bson

#JMT

async def patch_laia_base_model(element_id: str, patch_values: dict, model: Type, user_roles: list, repository: ModelRepository, use_access_rights: bool, user_shard: str = ""):
    """
    Partially updates one or more fields of a model instance.
    Unlike PUT (full update), PATCH only modifies the supplied fields
    and returns ONLY the patched fields + the element id.
    """
    _logger.info(f"Patching {model.__name__} with ID: {element_id} and fields: {list(patch_values.keys())}")

    # Normalize input to dict
    if hasattr(patch_values, "model_dump"):
        patch_values = patch_values.model_dump(exclude_unset=True)
    elif hasattr(patch_values, "dict"):
        patch_values = patch_values.dict(exclude_unset=True)
    elif not isinstance(patch_values, dict):
        patch_values = dict(patch_values)

    if not patch_values:
        raise ValueError("No fields provided to patch")

    # Validate that provided fields actually exist in the model
    valid_fields = set(model.model_fields.keys())
    invalid_fields = set(patch_values.keys()) - valid_fields
    if invalid_fields:
        raise ValueError(f"Invalid field(s) for {model.__name__}: {', '.join(invalid_fields)}")

    # Convert ObjectId fields
    patch_values = convert_objectid_fields(model, patch_values)

    model_name = model.__name__.lower()

    # Access rights check
    if "admin" not in user_roles and use_access_rights:
        access_rights_list = await check_access_rights_of_user(model_name, user_roles, "update", repository)
        await check_access_rights_of_fields(model, 'fields_edit', patch_values, access_rights_list)

    # Shard check
    extra = getattr(model, "model_config", {}).get("json_schema_extra", {})
    if extra.get("x-shard") and "admin" not in user_roles:
        shard_key = extra.get("x-shard-key", "region")
        if not user_shard or user_shard == "":
            raise ValueError("El usuario no tiene shard asignado, no puede actualizar este modelo shard")

        current_items = await repository.get_items(model_name, filters={"_id": ObjectId(element_id)}, limit=1)
        if isinstance(current_items, tuple):
            current = current_items[0]
        else:
            current = current_items
        if not current:
            raise ValueError(f"{model.__name__} with id {element_id} not found")

        current_doc = current[0]
        if current_doc.get(shard_key) != user_shard:
            raise ValueError("No tienes permiso para actualizar un registro de otra shard")

        patch_values[shard_key] = user_shard

    # Perform the patch via repository
    try:
        patched_fields = await repository.patch_item(model_name, element_id, patch_values)
    except KeyError as e:
        _logger.exception("Field error while patching %s: %s", model.__name__, e)
        raise ValueError(f"Invalid field(s) in patch: {e}") from e
    except ValueError as e:
        _logger.exception("Value error while patching %s: %s", model.__name__, e)
        raise
    except Exception as e:
        _logger.exception("Unexpected error patching %s with ID %s", model.__name__, element_id)
        raise

    # Filter by access rights if needed
    if "admin" not in user_roles and use_access_rights:
        allowed_fields = get_allowed_fields(access_rights_list, 'fields_visible')
        patched_fields = {field: patched_fields[field] for field in allowed_fields if field in patched_fields}

    _logger.info(f"{model.__name__} patched successfully (fields: {list(patch_values.keys())})")
    return serialize_bson(patched_fields)
