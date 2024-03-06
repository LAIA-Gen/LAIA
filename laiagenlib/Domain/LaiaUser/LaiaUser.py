from typing import Type, List, Dict, Any
from ..LaiaBaseModel.LaiaBaseModel import LaiaBaseModel

class LaiaUser(LaiaBaseModel):
    email: str = ""
    password: str
    roles: List[str] = []

    def __init__(self, email, password, roles):
        self.email = email
        self.password = password
        self.roles = roles
