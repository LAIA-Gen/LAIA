from typing import TypeVar, Optional, Dict
from pydantic import BaseModel
from pymongo.collection import ReturnDocument
from argapilib.schemas import list_serial, individual_serial
from bson import ObjectId
from argapilib.crud import CRUD

T = TypeVar('T', bound='BaseModel')

class CRUDMongoImpl(CRUD):

    def __init__(self, db: Dict[str, any]):
        super().__init__(db)

    async def get_items(self, model_name: str, skip: int = 0, limit: int = 10, filters: Optional[dict] = None, orders: Optional[dict] = None):
        collection = self.db[model_name]

        query = filters or {}
        sorts = orders or {}


        items = collection.find(query, skip=skip, limit=limit, sort=sorts)
        serialized_items = list_serial(items)

        total_count = collection.count_documents(query)
        
        return serialized_items, total_count
    
    async def get_item(self, model_name: str, item_id: str):
        collection = self.db[model_name]

        item = collection.find_one({'_id': ObjectId(item_id)})

        if item:
            return individual_serial(item)
        raise ValueError(f"{model_name} with ID {item_id} not found")

    async def post_item(self, model_name: str, item: T):
        collection = self.db[model_name]
        item_dict = dict(item)
        item_dict.pop('id', None)
        created_result = collection.insert_one(item_dict)
        inserted_id = created_result.inserted_id
        item_dict['id'] = str(inserted_id)
        item_dict.pop('_id', None)

        return item_dict

    async def put_item(self, model_name: str, item_id: str, update_fields: dict):
        collection = self.db[model_name]
        update_query = {'$set': update_fields}
        
        updated_item = collection.find_one_and_update(
            {'_id': ObjectId(item_id)},
            update_query,
            return_document=ReturnDocument.AFTER,
        )
        
        if updated_item:
            return individual_serial(updated_item)
        raise Exception

    async def delete_item(self, model_name: str, item_id: str):
        collection = self.db[model_name]
        deleted_item = collection.find_one_and_delete({'_id': ObjectId(item_id)})
        if deleted_item:
            return individual_serial(deleted_item)
        raise Exception
    