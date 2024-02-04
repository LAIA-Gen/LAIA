from typing import TypeVar
from .crud import CRUD
from .logger import _logger

T = TypeVar('T', bound='BaseModel')

async def create_element(element: T, crud_instance: CRUD):
    model_name = element.__class__.__name__.lower()

    return await crud_instance.post_item(model_name, element)
