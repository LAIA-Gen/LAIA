from typing import Type, List

from bson import ObjectId
from ..AccessRights.CheckAccessRightsOfUser import check_access_rights_of_user
from ...Domain.LaiaBaseModel.ModelRepository import ModelRepository
from ...Domain.Shared.Utils.logger import _logger

async def delete_laia_base_model(element_id: str, model: Type, user_roles: List[str], repository: ModelRepository, use_access_rights: bool, user_shard: str = ""):
    _logger.info(f"Deleting {model.__name__} with ID: {element_id}")

    model_name = model.__name__.lower()

    extra = getattr(model, "model_config", {}).get("json_schema_extra", {})
    if extra.get("x-shard") and "admin" not in user_roles:
        shard_key = extra.get("x-shard-key", "region")
        if not user_shard:
            raise ValueError("El usuario no tiene shard asignado, no puede eliminar en modelo shard")
        current_items = await repository.get_items(model_name, filters={"_id": ObjectId(element_id)}, limit=1)
        if isinstance(current_items, tuple):
            current = current_items[0]
        else:
            current = current_items
        if not current:
            raise ValueError(f"{model.__name__} with id {element_id} not found")
        current_doc = current[0]
        if current_doc.get(shard_key) != user_shard:
            raise ValueError("No tienes permiso para eliminar un registro de otra shard")

    if "admin" not in user_roles and use_access_rights:
        await check_access_rights_of_user(model_name, user_roles, "delete", repository)
    try:
        await repository.delete_item(model_name, element_id)
    except Exception:
        raise ValueError(f"{model.__name__} with ID does not exist, or there was an error deleting the element")

    _logger.info(f"{model.__name__} deleted successfully")