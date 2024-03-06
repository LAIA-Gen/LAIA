from typing import Dict
from pydantic import BaseModel

class AccessRight(BaseModel):
    role: str
    model: str
    operations: Dict[str, int] = {}
    fields_create: Dict[str, int] = {}
    fields_edit: Dict[str, int] = {}
    fields_visible: Dict[str, int] = {}

    def __init__(self, role, model, operations, fields_create, fields_edit, fields_visible):
        self.role = role
        self.model = model
        self.operations = operations
        self.fields_create = fields_create
        self.fields_edit = fields_edit
        self.fields_visible = fields_visible
