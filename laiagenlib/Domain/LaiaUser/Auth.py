from typing import TypeVar
from pydantic import BaseModel
from .LaiaUser import LaiaUser

T = TypeVar('T', bound='LaiaUser')

class Auth(BaseModel):
    email: str
    password: str
    