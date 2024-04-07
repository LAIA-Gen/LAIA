from typing import List
from pydantic import Field
from ..LaiaBaseModel.LaiaBaseModel import LaiaBaseModel

class LaiaUser(LaiaBaseModel):
    email: str
    password: str
    roles: List[str] = Field([], x_frontend_relation="Role")
