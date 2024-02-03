from typing import TypeVar, Type
from pydantic import BaseModel
from argapilib.crud import CRUD
from argapilib.logger import _logger

T = TypeVar('T', bound='BaseModel')

async def create_element(element: T, crud_instance: CRUD):
    model_name = element.__class__.__name__.lower()

    return await crud_instance.post_item(model_name, element)

class Model(BaseModel):
    name: str

    @classmethod
    async def create(cls, new_element, user_roles, crud_instance: CRUD):
        _logger.info("HEY YOU, I AM CREATING")
        return new_element
