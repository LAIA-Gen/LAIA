from typing import Dict
from ..LaiaBaseModel.LaiaBaseModel import LaiaBaseModel

ALLOWED_OPERATIONS = ["create", "read", "update", "delete", "search"]

class AccessRight(LaiaBaseModel):
    name: str = ""
    role: str
    model: str
    operations: Dict[str, int] = {}
    fields_create: Dict[str, int] = {}
    fields_edit: Dict[str, int] = {}
    fields_visible: Dict[str, int] = {}

    def __init__(self, **data):
        if "operations" in data:
            for operation in data["operations"]:
                if operation not in ALLOWED_OPERATIONS:
                    raise ValueError(f"Operation '{operation}' not allowed.")
        
        super().__init__(**data)
