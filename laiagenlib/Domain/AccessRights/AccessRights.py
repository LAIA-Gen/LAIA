from typing import Dict, Type
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from ..crud.crud import CRUD
from ..utils.logger import _logger
from ..utils.utils import create_element

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
