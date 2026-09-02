from typing import Type, List, Optional
from math import ceil

from laiagenlib.Domain.Shared.Utils.SerializeBson import serialize_bson
from ..AccessRights.CheckAccessRightsOfUser import check_access_rights_of_user
from ..AccessRights.GetAllowedFields import get_allowed_fields
from ..Shared.Utils.StripExcludedFields import strip_excluded_fields
from ...Domain.LaiaBaseModel.ModelRepository import ModelRepository
from ...Domain.Shared.Utils.logger import _logger
from ...Application.Hooks.HookExecutor import execute_hooks
from bson import ObjectId
#JMT


def _get_populate_excluded_fields(model: Type, field_name: str) -> List[str]:
    """Return response fields excluded by a relation's populate configuration."""
    config = getattr(model, "model_config", {})
    model_extra = config.get("json_schema_extra", {}) if isinstance(config, dict) else {}
    configured_by_field = (
        model_extra.get("x-populate-exclude-fields", {})
        if isinstance(model_extra, dict)
        else {}
    )
    configured_fields = (
        configured_by_field.get(field_name, [])
        if isinstance(configured_by_field, dict)
        else []
    )

    field = getattr(model, "model_fields", {}).get(field_name)
    if field is None:
        return configured_fields if isinstance(configured_fields, list) else []

    extra = getattr(field, "json_schema_extra", None) or {}
    populate_config = extra.get("populate", {}) if isinstance(extra, dict) else {}
    if not isinstance(populate_config, dict):
        return configured_fields if isinstance(configured_fields, list) else []

    excluded = populate_config.get(
        "excludeFields",
        populate_config.get("exclude_fields", configured_fields),
    )
    if not isinstance(excluded, list):
        return []
    return [name for name in excluded if isinstance(name, str)]


def _strip_named_fields(data, excluded_fields: List[str]):
    if not excluded_fields:
        return data
    excluded = set(excluded_fields)
    if isinstance(data, list):
        return [_strip_named_fields(item, excluded_fields) for item in data]
    if isinstance(data, dict):
        return {key: value for key, value in data.items() if key not in excluded}
    return data


async def search_laia_base_model(skip: int, limit: int, filters: dict, orders: dict, model: Type, user_roles: List[str], repository: ModelRepository, user_id: str = '', use_access_rights: bool = True, use_ontology: bool = False, user_shard: str = "", populate: Optional[List] = None, smtp_config: dict = None):
    _logger.info(f"Searching {model.__name__} with filters: {filters}")

    model_name = model.__name__.lower()
    config = getattr(model, "model_config", {})
    extra = config.get("json_schema_extra", {}) if isinstance(config, dict) else (getattr(config, "json_schema_extra", {}) or {})

    is_public = False
    if isinstance(extra, dict):
        permissions = extra.get("x-permissions", {})
        if isinstance(permissions, dict):
            is_public = permissions.get("search") == []

    if "admin" not in user_roles and use_access_rights and not is_public:
        access_rights_list = await check_access_rights_of_user(model_name, user_roles, "search", repository)
        _logger.info("USER ID: " + user_id)
        _logger.info(access_rights_list)
        if not any(not access_right.owner for access_right in access_rights_list):
            _logger.info("HEY")
            owner_fields = extra.get("x-owner-fields", ["owner"])
            if len(owner_fields) == 1:
                filters[owner_fields[0]] = ObjectId(user_id)
            else:
                filters["$or"] = [{field: ObjectId(user_id)} for field in owner_fields]

    if extra.get("x-shard") and "admin" not in user_roles:
        shard_key = extra.get("x-shard-key", "region")
        filters[shard_key] = user_shard

    filters = await execute_hooks(
        "presearch",
        model,
        filters,
        smtp_config,
        repository,
        context_extra={"user_roles": user_roles, "user_id": user_id},
    )

    if "_id" in filters and isinstance(filters["_id"], str):
        filters["_id"] = ObjectId(filters["_id"])
    elif "id" in filters and isinstance(filters["id"], str):
        filters["_id"] = ObjectId(filters.pop("id"))
    try:
        items, total_count = await repository.get_items(model_name, skip=skip, limit=limit, filters=filters, orders=orders, populate=populate)
        if "admin" not in user_roles and use_access_rights and not is_public:
            allowed_fields = get_allowed_fields(access_rights_list, 'fields_visible')
            items = [
                {field: item[field] for field in allowed_fields if field in item}
                for item in items
            ]
        max_pages = ceil(total_count / limit)
        current_page = (skip // limit) + 1
        context = {}
        if use_ontology:
            extra = getattr(model, "model_config", {}).get("json_schema_extra", {})
            context = extra.get("@context", {})
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise ValueError(f"Error occurred while searching {model.__name__} with filters: {filters}. Details: {str(e)}")
    
    if populate:
        from ...Domain.Shared.Utils.ModelRegistry import get_model_class
        for entry in populate:
            fields_to_exclude = []
            if isinstance(entry, dict):
                local_field = entry.get("id") or entry.get("field")
                from_col = entry.get("from", local_field)
                result_field = entry.get("as", local_field)
                fields_to_exclude = entry.get("excludeFields") or entry.get("exclude_fields") or []
            else:
                local_field = entry
                from_col = entry
                result_field = entry

            populated_model = get_model_class(from_col)
            relation_excluded_fields = _get_populate_excluded_fields(model, local_field)
            for item in items:
                if result_field in item and item[result_field] is not None:
                    if populated_model:
                        item[result_field] = strip_excluded_fields(populated_model, item[result_field])
                    item[result_field] = _strip_named_fields(
                        item[result_field], list(set(relation_excluded_fields + fields_to_exclude))
                    )

    items = strip_excluded_fields(model, items)
    serialized_items = []
    for item in items:
        serialized_items.append(serialize_bson(item))

    _logger.info(f"{model.__name__} search completed successfully")
    response = {
        "items": serialized_items,
        "current_page": current_page,
        "max_pages": max_pages,
    }

    if use_ontology:
        response["@context"] = context

    return response
