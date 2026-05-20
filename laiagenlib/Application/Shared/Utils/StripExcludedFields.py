from typing import Type, Union


def strip_excluded_fields(model: Type, data: Union[dict, list]) -> Union[dict, list]:
    extra = getattr(model, "model_config", {}).get("json_schema_extra", {})
    excluded = extra.get("x-exclude-from-response", [])
    if not excluded:
        return data
    if isinstance(data, list):
        return [{k: v for k, v in item.items() if k not in excluded} for item in data]
    if isinstance(data, dict):
        return {k: v for k, v in data.items() if k not in excluded}
    return data
