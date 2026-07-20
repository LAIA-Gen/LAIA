from typing import Annotated, Type, Union, get_origin

from bson import ObjectId
from fastapi import HTTPException, types

from laiagenlib.Domain.Shared.Utils.SerializeBson import serialize_bson
from ..AccessRights.CheckAccessRightsOfUser import check_access_rights_of_user
from ..AccessRights.CheckAccessRightsOfFields import check_access_rights_of_fields
from ..AccessRights.GetAllowedFields import get_allowed_fields
from ..Shared.Utils.StripExcludedFields import strip_excluded_fields
from ...Domain.LaiaBaseModel.ModelRepository import ModelRepository
from ...Domain.Shared.Utils.logger import _logger
from fastapi.encoders import jsonable_encoder
from typing import get_args

from ...Application.Hooks.HookExecutor import execute_hooks


def _has_hooks(model: Type, event: str) -> bool:
    extra = getattr(model, "model_config", {}).get("json_schema_extra", {})
    hooks = extra.get("x-hooks", {}) if isinstance(extra, dict) else {}
    if hooks.get(event):
        return True
    normalized_event = event.lower()
    return any(str(configured_event).lower() == normalized_event for configured_event in hooks)


async def _get_current_doc(model_name: str, element_id: str, repository: ModelRepository) -> dict:
    current_items = await repository.get_items(model_name, filters={"_id": ObjectId(element_id)}, limit=1)
    current = current_items[0] if isinstance(current_items, tuple) else current_items
    if not current:
        raise ValueError(f"{model_name} with id {element_id} not found")
    return current[0]


def _hook_update_fields(before: dict, after: dict, model: Type) -> dict:
    field_names = set(getattr(model, "model_fields", {}).keys())
    blocked = {"id", "_id"}
    changes = {}

    for key, value in after.items():
        if key in blocked:
            continue
        if field_names and key not in field_names:
            continue
        if before.get(key) != value:
            changes[key] = value

    return changes

def _contains_objectid(ann) -> bool:
    if ann is ObjectId:
        return True

    origin = get_origin(ann)
    if origin in (Union, types.UnionType):
        return any(_contains_objectid(a) for a in get_args(ann))

    if origin is Annotated:
        base, *_meta = get_args(ann)
        return _contains_objectid(base)

    return False

def _contains_objectid_stringy(ann) -> bool:
    rep = repr(ann)
    return ("bson.objectid.ObjectId" in rep) or ("ObjectId" in rep)

def convert_objectid_fields(model, values: dict) -> dict:
    for field_name, field in model.model_fields.items():
        ann = field.annotation

        is_oid = _contains_objectid(ann)

        if not is_oid:
            is_oid = _contains_objectid_stringy(ann)

        if is_oid:
            v = values.get(field_name, None)
            if v is None:
                continue
            else:
                try:
                    values[field_name] = ObjectId(v)
                except Exception:
                    pass
    return values

async def update_laia_base_model(element_id:str, updated_values: dict, model: Type, user_roles: list, repository: ModelRepository, use_access_rights: bool = True, user_shard: str = "", smtp_config: dict = None, user_id: str = ""):
    _logger.info(f"Updating {model.__name__} with ID: {element_id} and values: {updated_values}")

    if hasattr(updated_values, "model_dump"):            
        updated_values = updated_values.model_dump(exclude_unset=True)
    elif hasattr(updated_values, "dict"):               
        updated_values = updated_values.dict(exclude_unset=True)
    elif not isinstance(updated_values, dict):
        updated_values = dict(updated_values)

    updated_values = convert_objectid_fields(model, updated_values)

    model_name = model.__name__.lower()

    access_rights_list = []
    if "admin" not in user_roles and use_access_rights:
        access_rights_list = await check_access_rights_of_user(model_name, user_roles, "update", repository)
        await check_access_rights_of_fields(model, 'fields_edit', updated_values, access_rights_list)

    extra = getattr(model, "model_config", {}).get("json_schema_extra", {})
    configured_owner_fields = extra.get("x-owner-fields") if isinstance(extra, dict) else None
    has_configured_owner_fields = isinstance(configured_owner_fields, list) and len(configured_owner_fields) > 0
    needs_shard_check = extra.get("x-shard") and "admin" not in user_roles
    needs_owner_check = "admin" not in user_roles and (
        (use_access_rights and not any(not access_right.owner for access_right in access_rights_list))
        or (not use_access_rights and has_configured_owner_fields)
    )

    current_doc = None

    if needs_shard_check or needs_owner_check:
        current_doc = await _get_current_doc(model_name, element_id, repository)

        if needs_shard_check:
            shard_key = extra.get("x-shard-key", "region")
            if not user_shard or user_shard == "":
                raise ValueError("El usuario no tiene shard asignado, no puede actualizar este modelo shard")
            if current_doc.get(shard_key) != user_shard:
                raise ValueError("No tienes permiso para actualizar un registro de otra shard")
            updated_values[shard_key] = user_shard
            
        if needs_owner_check:
            owner_fields = configured_owner_fields if has_configured_owner_fields else ["owner"]
            is_owner = False
            for field in owner_fields:
                val = current_doc.get(field)
                if isinstance(val, list):
                    if any(str(v) == str(user_id) for v in val):
                        is_owner = True
                        break
                elif str(val) == str(user_id):
                    is_owner = True
                    break
            if not is_owner:
                raise PermissionError("You do not have permission to update this record; you are not the owner")

    try:
        if _has_hooks(model, "preupdate"):
            if current_doc is None:
                current_doc = await _get_current_doc(model_name, element_id, repository)

            proposed_element = {**current_doc, **updated_values}
            before_preupdate = dict(proposed_element)
            proposed_element = await execute_hooks(
                "preupdate", model, proposed_element, smtp_config, repository
            )
            updated_values.update(_hook_update_fields(before_preupdate, proposed_element, model))

        updated_element = await repository.put_item(model_name, element_id, updated_values)
        
        if _has_hooks(model, "postupdate"):
            before_postupdate = dict(updated_element)
            updated_element = await execute_hooks("postupdate", model, updated_element, smtp_config, repository)
            hook_changes = _hook_update_fields(before_postupdate, updated_element, model)
            if hook_changes:
                updated_element = await repository.put_item(model_name, element_id, hook_changes)
        
    except KeyError as e:
        _logger.exception("Field error while updating %s: %s", model.__name__, e)
        raise ValueError(f"Invalid field(s) in update: {e}") from e
    except HTTPException:
        raise
    except ValueError as e:
        _logger.exception("Value error while updating %s: %s", model.__name__, e)
        raise
    except Exception as e:
        _logger.exception("Unexpected error updating %s with ID %s", model.__name__, element_id)
        raise 
    
    if "admin" not in user_roles and use_access_rights:
        allowed_fields = get_allowed_fields(access_rights_list, 'fields_visible')
        updated_element = {field: updated_element[field] for field in allowed_fields if field in updated_element}

    _logger.info(f"{model.__name__} updated successfully")
    return serialize_bson(strip_excluded_fields(model, updated_element))
