from typing import TypeVar, Optional, Dict
from datetime import datetime
from enum import Enum
from pydantic import BaseModel
from bson import ObjectId, regex
from pymongo.collection import ReturnDocument
import json
from ...Application.Shared.Utils.Schemas import list_serial, individual_serial
from ...Domain.LaiaBaseModel.ModelRepository import ModelRepository
from ...Domain.Shared.Utils.logger import _logger


T = TypeVar('T', bound='BaseModel')

class PostgreModelRepository(ModelRepository):

    def __init__(self, db: Dict[str, any]):
        super().__init__(db)

    async def get_items(self, model_name: str, skip: int = 0, limit: int = 10, filters: Optional[dict] = None, orders: Optional[dict] = None):
        pass
    
    async def get_item(self, model_name: str, item_id: str):
        pass

    async def post_item(self, model_name: str, item: T):
        pass

    async def put_item(self, model_name: str, item_id: str, update_fields: dict):
        pass

    async def delete_item(self, model_name: str, item_id: str):
        pass