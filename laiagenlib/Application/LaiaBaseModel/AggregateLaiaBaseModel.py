from typing import Type, List
from bson import ObjectId
from laiagenlib.Domain.Shared.Utils.SerializeBson import serialize_bson
from ..AccessRights.CheckAccessRightsOfUser import check_access_rights_of_user
from ..AccessRights.GetAllowedFields import get_allowed_fields
from ...Domain.LaiaBaseModel.ModelRepository import ModelRepository
from ...Domain.Shared.Utils.logger import _logger

def convert_ids_in_pipeline(pipeline: list) -> list:
    for stage in pipeline:
        if "$match" in stage:
            for field, value in stage["$match"].items():
                if isinstance(value, str) and len(value) == 24:
                    try:
                        stage["$match"][field] = ObjectId(value)
                    except:
                        pass
    return pipeline

async def aggregate_laia_base_model(
    pipeline: list,
    model: Type,
    user_roles: List[str],
    repository: ModelRepository,
    user_id: str = '',
    use_access_rights: bool = True,
    use_ontology: bool = False
):
    _logger.info(f"Aggregating {model.__name__} with pipeline: {pipeline}")

    model_name = model.__name__.lower()

    pipeline = convert_ids_in_pipeline(pipeline)

    if "admin" not in user_roles and use_access_rights:
        access_rights_list = await check_access_rights_of_user(model_name, user_roles, "aggregate", repository)
        _logger.info("USER ID: " + str(user_id))
        _logger.info(access_rights_list)
        if not any(not access_right.owner for access_right in access_rights_list):
            match_stage = {"$match": {"owner": ObjectId(user_id)}}
            pipeline.insert(0, match_stage)

    try:
        results = await repository.aggregate_items(model_name, pipeline)
    except Exception as e:
        raise ValueError(f"Error occurred while aggregating {model.__name__} with pipeline: {pipeline}. Error: {str(e)}")

    serialized_results = [serialize_bson(item) for item in results]

    _logger.info(f"{model.__name__} aggregation completed successfully")
    response = {"results": serialized_results}

    if use_ontology:
        extra = getattr(model, "model_config", {}).get("json_schema_extra", {})
        response["@context"] = extra.get("@context", {})

    return response
