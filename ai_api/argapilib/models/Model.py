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
    async def create(cls, new_element: dict, model: Type, user_roles: list, crud_instance: CRUD):
        _logger.info(f"Creating new {model.__name__} with values: {new_element}")

        required_params = cls.__annotations__.keys()
        missing_params = set(required_params) - set(new_element.keys())
        if missing_params:
            raise ValueError(f"Missing required parameters: {', '.join(missing_params)}")
        
        element = model(**new_element)
        created_element = await create_element(element, crud_instance)
        _logger.info(f"{model.__name__} created successfully")
        return cls(**created_element)
