from typing import List
from pydantic import BaseModel, Field

from laiagenlib.Application import LaiaBaseModel

class LaiaUser(LaiaBaseModel):
    email: str
    password: str
    roles: List[str] = Field([], x_frontend_relation="Role")
