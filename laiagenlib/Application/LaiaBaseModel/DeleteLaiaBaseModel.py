from typing import Type, List, Optional

from bson import ObjectId
from ..AccessRights.CheckAccessRightsOfUser import check_access_rights_of_user
from ...Domain.LaiaBaseModel.ModelRepository import ModelRepository
from ...Domain.Shared.Utils.logger import _logger
from ...Application.Hooks.HookExecutor import execute_hooks

def _has_hooks(model: Type, event: str) -> bool:
    extra = getattr(model, "model_config", {}).get("json_schema_extra", {})
    hooks = extra.get("x-hooks", {}) if isinstance(extra, dict) else {}
    if hooks.get(event):
        return True
    normalized_event = event.lower()
    return any(str(configured_event).lower() == normalized_event for configured_event in hooks)

async def delete_laia_base_model(element_id: str, model: Type, user_roles: List[str], repository: ModelRepository, use_access_rights: bool = True, user_shard: str = "", user_id: str = "", smtp_config: Optional[dict] = None):
    _logger.info(f"Deleting {model.__name__} with ID: {element_id}")

    model_name = model.__name__.lower()

    access_rights_list = []
    if "admin" not in user_roles and use_access_rights:
        access_rights_list = await check_access_rights_of_user(model_name, user_roles, "delete", repository)

    extra = getattr(model, "model_config", {}).get("json_schema_extra", {})
    needs_shard_check = extra.get("x-shard") and "admin" not in user_roles
    needs_owner_check = "admin" not in user_roles and use_access_rights and not any(not access_right.owner for access_right in access_rights_list)
    has_predelete = _has_hooks(model, "predelete")
    current_doc = None

    if needs_shard_check or needs_owner_check or has_predelete:
        current_items = await repository.get_items(model_name, filters={"_id": ObjectId(element_id)}, limit=1)
        if isinstance(current_items, tuple):
            current = current_items[0]
        else:
            current = current_items
        if not current:
            raise ValueError(f"{model.__name__} with id {element_id} not found")
        current_doc = current[0]
        
        if needs_shard_check:
            shard_key = extra.get("x-shard-key", "region")
            if not user_shard:
                raise ValueError("El usuario no tiene shard asignado, no puede eliminar en modelo shard")
            if current_doc.get(shard_key) != user_shard:
                raise ValueError("No tienes permiso para eliminar un registro de otra shard")

        if needs_owner_check:
            owner_fields = extra.get("x-owner-fields", ["owner"]) if isinstance(extra, dict) else ["owner"]
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
                raise PermissionError("No tienes permiso para eliminar este registro, no eres el propietario")

    if has_predelete:
        await execute_hooks("predelete", model, current_doc, smtp_config, repository)

    try:
        await repository.delete_item(model_name, element_id)
    except Exception:
        raise ValueError(f"{model.__name__} with ID does not exist, or there was an error deleting the element")

    _logger.info(f"{model.__name__} deleted successfully")