from typing import Dict
from pydantic import BaseModel

class Role(BaseModel):
    name: str

    def __init__(self, name):
        self.name = name
