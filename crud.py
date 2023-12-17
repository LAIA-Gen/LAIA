from typing import TypeVar, Optional
from pydantic import BaseModel

T = TypeVar('T', bound='BaseModel')

class CRUD:

    async def get_items(model_name: str, skip: int = 0, limit: int = 10, filters: Optional[dict] = None):
        pass

    async def get_item(model_name: str, item_id: str):
        pass

    async def post_item(model_name: str, item: T):
        pass

    async def put_item(model_name: str, item_id: str, item: T):
        pass

    async def delete_item(model_name: str, item_id: str):
        pass