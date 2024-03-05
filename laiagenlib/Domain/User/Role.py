from typing import Dict
from pydantic import BaseModel
from ..crud.crud import CRUD
from ..utils.logger import _logger
from ..utils.utils import create_element

class Role(BaseModel):
    name: str

    def __init__(self, name):
        self.name = name
