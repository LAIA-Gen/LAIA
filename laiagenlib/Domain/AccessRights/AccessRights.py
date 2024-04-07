from typing import Dict, Optional
from pydantic import Field
from ..LaiaBaseModel.LaiaBaseModel import LaiaBaseModel

ALLOWED_OPERATIONS = ["create", "read", "update", "delete", "search"]

class AccessRight(LaiaBaseModel):
    name: str = ""
    role: Optional[str] = Field("", x_frontend_relation="Role", x_frontend_fieldName="Role")
    model: Optional[str] = Field("", x_frontend_widget='ModelsSelectableWidget', x_frontend_fieldName="Model")
    operations: Dict = Field({}, x_frontend_placeholder="{'create': 1, 'read': 1, 'update': 0, 'delete': 0, 'search': 1}", x_frontend_fieldName="Operations Permitted")
    fields_create: Dict = Field({}, x_frontend_placeholder="{'field_1': 1, 'field_2': 1, 'field_3': 0, ...}", x_frontend_fieldName="Fields Creation")
    fields_edit: Dict = Field({}, x_frontend_placeholder="{'field_1': 1, 'field_2': 1, 'field_3': 0, ...}", x_frontend_fieldName="Fields Edition")
    fields_visible: Dict = Field({}, x_frontend_placeholder="{'field_1': 1, 'field_2': 1, 'field_3': 0, ...}", x_frontend_fieldName="Fields Visibility")

    def __init__(self, **data):
        if "operations" in data:
            for operation in data["operations"]:
                if operation not in ALLOWED_OPERATIONS:
                    raise ValueError(f"Operation '{operation}' not allowed.")
        
        super().__init__(**data)
