from typing import Type, List, Dict, Any
import bcrypt
from ..utils.utils import validate_email, validate_password
from ..crud.crud import CRUD
from .AccessRights import AccessRight
from .Model import LaiaBaseModel
from ..utils.logger import _logger

class LaiaUser(LaiaBaseModel):
    email: str = ""
    password: str
    roles: List[str] = []

    def __init__(self, email, password, roles):
        self.email = email
        self.password = password
        self.roles = roles
