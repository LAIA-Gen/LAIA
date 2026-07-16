from typing import Type, List, Optional
from math import ceil

from laiagenlib.Domain.Shared.Utils.SerializeBson import serialize_bson
from ..AccessRights.CheckAccessRightsOfUser import check_access_rights_of_user
from ..AccessRights.GetAllowedFields import get_allowed_fields
from ..Shared.Utils.StripExcludedFields import strip_excluded_fields
from ...Domain.LaiaBaseModel.ModelRepository import ModelRepository
from ...Domain.Shared.Utils.logger import _logger
from bson import ObjectId
#JMT
async def search_laia_base_model(skip: int, limit: int, filters: dict, orders: dict, model: Type, user_roles: List[str], repository: ModelRepository, user_id: str = '', use_access_rights: bool = True, use_ontology: bool = False, user_shard: str = "", populate: Optional[List] = None):
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
            if isinstance(entry, dict):
                local_field = entry.get("id") or entry.get("field")
                from_col = entry.get("from", local_field)
                result_field = entry.get("as", local_field)
            else:
                local_field = entry
                from_col = entry
                result_field = entry

            populated_model = get_model_class(from_col)
            if populated_model:
                for item in items:
                    if result_field in item and item[result_field] is not None:
                        item[result_field] = strip_excluded_fields(populated_model, item[result_field])

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