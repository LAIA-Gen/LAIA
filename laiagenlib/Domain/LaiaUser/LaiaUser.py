from typing import List
from ..LaiaBaseModel.LaiaBaseModel import LaiaBaseModel

class LaiaUser(LaiaBaseModel):
    email: str
    password: str
    roles: List[str] = []
