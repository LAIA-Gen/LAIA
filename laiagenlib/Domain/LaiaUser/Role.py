from typing import Dict
from pydantic import BaseModel

class Role(BaseModel):
    name: str
