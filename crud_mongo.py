from typing import TypeVar, Optional
from pydantic import BaseModel
from pymongo.collection import ReturnDocument
from database import db
from schemas import list_serial, individual_serial
from bson import ObjectId
from crud import CRUD

T = TypeVar('T', bound='BaseModel')

class CRUDMongoImpl(CRUD):

    async def get_items(model_name: str, skip: int = 0, limit: int = 10, filters: Optional[dict] = None):
        collection = db[model_name]

        query = filters or {}
        print(query)

        items = collection.find(query, skip=skip, limit=limit)
        serialized_items = list_serial(items)

        return serialized_items
    
    async def get_item(model_name: str, item_id: str):
        collection = db[model_name]

        item = collection.find_one({'_id': ObjectId(item_id)})

        if item:
            return individual_serial(item)
        raise Exception

    async def post_item(model_name: str, item: T):
        collection = db[model_name]
        created_result = collection.insert_one(dict(item))
        inserted_id = created_result.inserted_id
        item_dict = dict(item)
        item_dict['id'] = str(inserted_id)
        return item_dict

    async def put_item(model_name: str, item_id: str, item: T):
        collection = db[model_name]
        updated_item = collection.find_one_and_update({'_id': ObjectId(item_id)},{'$set': dict(item)}, return_document=ReturnDocument.AFTER,)
        if updated_item:
            return individual_serial(updated_item)
        raise Exception

    async def delete_item(model_name: str, item_id: str):
        collection = db[model_name]
        deleted_item = collection.find_one_and_delete({'_id': ObjectId(item_id)})
        if deleted_item:
            return individual_serial(deleted_item)
        raise Exception