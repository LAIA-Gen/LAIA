from typing import Type, List, Dict, Any
from pydantic import BaseModel
from math import ceil
from ..utils.utils import create_element
from ..crud.crud import CRUD
from .AccessRights import AccessRight
from ..utils.logger import _logger

class LaiaBaseModel(BaseModel):
    id: str = ""
    name: str

    def __init__(self, id, name):
        self.id = id
        self.name = name
