from typing import List
from pydantic import BaseModel, Field

class LaiaUser(BaseModel):
    email: str
    password: str
    roles: List[str] = Field([], x_frontend_relation="Role")
