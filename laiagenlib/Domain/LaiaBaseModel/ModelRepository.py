from typing import TypeVar, Optional, Dict
from pydantic import BaseModel

T = TypeVar('T', bound='BaseModel')

class ModelRepository:

    def __init__(self, db: Dict[str, any]):
        self.db = db

    async def get_items(model_name: str, skip: int = 0, limit: int = 10, filters: Optional[dict] = None, orders: Optional[dict] = None):
        pass

    async def get_item(model_name: str, item_id: str):
        pass

    async def post_item(model_name: str, item: T):
        pass

    async def put_item(model_name: str, item_id: str, update_fields: dict):
        pass

    async def delete_item(model_name: str, item_id: str):
        pass