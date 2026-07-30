from typing import List, Type

from ....Domain.LaiaBaseModel.ModelRepository import ModelRepository


def _get_unique_constraints(model: Type) -> List[List[str]]:
    config = getattr(model, "model_config", {})
    extra = config.get("json_schema_extra", {}) if isinstance(config, dict) else {}
    configured = extra.get("x-unique-fields", []) if isinstance(extra, dict) else []

    if not configured:
        return []
    if all(isinstance(field, str) for field in configured):
        return [configured]
    if all(
        isinstance(constraint, list)
        and constraint
        and all(isinstance(field, str) for field in constraint)
        for constraint in configured
    ):
        return configured
    raise ValueError(
        f"{model.__name__} x-unique-fields must be a list of field names "
        "or a list of field-name lists"
    )


async def ensure_unique_constraints(
    model: Type,
    model_name: str,
    repository: ModelRepository,
) -> None:
    for fields in _get_unique_constraints(model):
        await repository.ensure_unique_constraint(model_name, fields)
