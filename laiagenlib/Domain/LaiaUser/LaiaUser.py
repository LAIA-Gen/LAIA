from typing import List
from pydantic import BaseModel, Field

from ..LaiaBaseModel.LaiaBaseModel import LaiaBaseModel

class LaiaUser(LaiaBaseModel):
    email: str
    password: str
    roles: List[str] = Field([], x_frontend_relation="Role")
