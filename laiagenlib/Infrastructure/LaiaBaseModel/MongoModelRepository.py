from typing import TypeVar, Optional, Dict
from enum import Enum
from pydantic import BaseModel
from bson import ObjectId, regex
from pymongo.collection import ReturnDocument
import json
from ...Application.Shared.Utils.Schemas import list_serial, individual_serial
from ...Domain.LaiaBaseModel.ModelRepository import ModelRepository
from ...Domain.Shared.Utils.logger import _logger


T = TypeVar('T', bound='BaseModel')

class MongoModelRepository(ModelRepository):

    def __init__(self, db: Dict[str, any]):
        super().__init__(db)

    async def get_items(self, model_name: str, skip: int = 0, limit: int = 10, filters: Optional[dict] = None, orders: Optional[dict] = None):
        collection = self.db[model_name]

        query = filters or {}
        sorts = orders or {}

        if 'id' in query:
            id_filter = query.pop('id')
            if isinstance(id_filter, dict):
                if '$in' in id_filter:
                    query['_id'] = {'$in': [ObjectId(id_) for id_ in id_filter['$in']]}
                elif '$nin' in id_filter:
                    query['_id'] = {'$nin': [ObjectId(id_) for id_ in id_filter['$nin']]}
            else:
                query['_id'] = {'$in': [ObjectId(id_filter)]}

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
        item_dict = json.loads(json.dumps(item_dict, default=lambda o: o.value if isinstance(o, Enum) else o))
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
    