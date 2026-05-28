"""
Global registry that maps collection names (lowercase model names)
to their Pydantic model classes. Populated during route creation
so that other layers can look up model metadata (e.g. x-exclude-from-response)
without needing direct access to the model classes.
"""

_model_registry: dict = {}


def register_model(collection_name: str, model_class):
    """Register a model class under its collection name."""
    _model_registry[collection_name.lower()] = model_class


def get_model_class(collection_name: str):
    """Return the model class for a collection name, or None."""
    return _model_registry.get(collection_name.lower())


def get_excluded_fields(collection_name: str) -> list:
    """Return the list of x-exclude-from-response fields for a collection."""
    model = get_model_class(collection_name)
    if not model:
        return []
    extra = getattr(model, "model_config", {}).get("json_schema_extra", {})
    if not isinstance(extra, dict):
        return []
    return extra.get("x-exclude-from-response", [])
