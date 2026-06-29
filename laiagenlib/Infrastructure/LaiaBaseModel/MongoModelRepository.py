from typing import Any, List, TypeVar, Optional, Dict
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

class MongoModelRepository(ModelRepository):

    def __init__(self, db: Dict[str, any]):
        super().__init__(db)

    def convert_dates_in_query(self, query: dict):
        def conv(v):
            if isinstance(v, str) and "T" in v:
                if v.endswith("Z"):
                    v2 = v[:-1] + "+00:00"
                else:
                    v2 = v
                try:
                    return datetime.fromisoformat(v2)
                except ValueError:
                    return v
            return v

        for k, v in list(query.items()):
            if isinstance(v, dict):
                for op, vv in list(v.items()):
                    v[op] = conv(vv)
            else:
                query[k] = conv(v)
#JMT
    def convert_objectids_in_query(self, query: dict):
        for k, v in list(query.items()):
            if isinstance(v, str) and len(v) == 24:
                try:
                    query[k] = ObjectId(v)
                except Exception:
                    pass
            elif isinstance(v, dict):
                for op, vv in list(v.items()):
                    if isinstance(vv, str) and len(vv) == 24:
                        try:
                            v[op] = ObjectId(vv)
                        except Exception:
                            pass
                    elif isinstance(vv, list):
                        new_list = []
                        for item in vv:
                            if isinstance(item, str) and len(item) == 24:
                                try:
                                    new_list.append(ObjectId(item))
                                except Exception:
                                    new_list.append(item)
                            else:
                                new_list.append(item)
                        v[op] = new_list

    def convert_enums_in_query(self, data: any) -> any:
        if isinstance(data, Enum):
            return data.value
        elif isinstance(data, dict):
            return {k: self.convert_enums_in_query(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self.convert_enums_in_query(v) for v in data]
        return data

    async def get_items(self, model_name: str, skip: int = 0, limit: int = 10, filters: Optional[dict] = None, orders: Optional[dict] = None, populate: Optional[List[str]] = None):
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

        self.convert_dates_in_query(query)
        self.convert_objectids_in_query(query)

        if populate:
            # Identificar campos populados para saber cómo dividir los filtros
            populated_fields = set()
            for entry in populate:
                if isinstance(entry, dict):
                    local_field = entry.get("id") or entry.get("field")
                    result_field = entry.get("as", local_field)
                else:
                    result_field = entry
                populated_fields.add(result_field)

            # Separar filtros base de filtros post-lookup (aquellos con formato "campo_populado.subcampo")
            base_query = {}
            post_lookup_query = {}
            for k, v in query.items():
                parts = k.split('.', 1)
                if len(parts) > 1 and parts[0] in populated_fields:
                    post_lookup_query[k] = v
                else:
                    base_query[k] = v

            lookup_stages = []
            for entry in populate:
                if isinstance(entry, dict):
                    local_field = entry.get("id") or entry.get("field")
                    from_col = entry.get("from", local_field)
                    result_field = entry.get("as", local_field)
                    fields_to_keep = entry.get("fields", [])
                else:
                    local_field = entry
                    from_col = entry
                    result_field = entry
                    fields_to_keep = []

                col_names = self.db.list_collection_names()
                actual_col = from_col
                if from_col not in col_names:
                    for c in col_names:
                        if c.lower() == from_col.lower():
                            actual_col = c
                            break

                temp_field = f"_{result_field.replace('.', '_')}_populated"
                
                # Conversion
                lookup_stages.append({
                    "$addFields": {
                        f"{local_field}_as_obj": {
                            "$cond": {
                                "if": {"$isArray": f"${local_field}"},
                                "then": {
                                    "$map": {
                                        "input": f"${local_field}",
                                        "as": "id_val",
                                        "in": {
                                            "$convert": {
                                                "input": "$$id_val",
                                                "to": "objectId",
                                                "onError": None,
                                                "onNull": None
                                            }
                                        }
                                    }
                                },
                                "else": {
                                    "$cond": {
                                        "if": { "$and": [{ "$ne": [f"${local_field}", None] }, { "$ne": [f"${local_field}", ""] }] },
                                        "then": {
                                            "$convert": {
                                                "input": f"${local_field}",
                                                "to": "objectId",
                                                "onError": None,
                                                "onNull": None
                                            }
                                        },
                                        "else": None
                                    }
                                }
                            }
                        }
                    }
                })

                # Lookups
                lookup_stages.append({
                    "$lookup": {
                        "from": actual_col,
                        "localField": f"{local_field}_as_obj",
                        "foreignField": "_id",
                        "as": temp_field
                    }
                })

                # Projection (if fields are specified)
                if fields_to_keep:
                    projection = {f: f"$$item.{f}" for f in fields_to_keep}
                    if "_id" not in fields_to_keep and "id" not in fields_to_keep:
                        projection["_id"] = "$$item._id"
                    
                    lookup_stages.append({
                        "$set": {
                            temp_field: {
                                "$map": {
                                    "input": f"${temp_field}",
                                    "as": "item",
                                    "in": projection
                                }
                            }
                        }
                    })

                # Final field assignment
                lookup_stages.append({
                    "$addFields": {
                        result_field: {
                            "$cond": {
                                "if": {"$isArray": f"${local_field}"},
                                "then": f"${temp_field}",
                                "else": {"$arrayElemAt": [f"${temp_field}", 0]}
                            }
                        }
                    }
                })
                # Clean up intermediate fields
                lookup_stages.append({"$project": {temp_field: 0, f"{local_field}_as_obj": 0}})

            pipeline = [{"$match": base_query}]
            pipeline.extend(lookup_stages)

            if post_lookup_query:
                pipeline.append({"$match": post_lookup_query})

            if sorts:
                pipeline.append({"$sort": sorts})
            
            pipeline.append({"$skip": skip})
            pipeline.append({"$limit": limit})

            items = collection.aggregate(pipeline)
            serialized_items = list_serial(items)

            if post_lookup_query:
                count_pipeline = [{"$match": base_query}]
                count_pipeline.extend(lookup_stages)
                count_pipeline.append({"$match": post_lookup_query})
                count_pipeline.append({"$count": "count"})
                
                count_res = list(collection.aggregate(count_pipeline))
                total_count = count_res[0]["count"] if count_res else 0
            else:
                total_count = collection.count_documents(query)
        else:
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

        if hasattr(item, 'model_dump'):
            item_dict = item.model_dump(mode="python")
        else:
            item_dict = dict(item)

        item_dict.pop('id', None)
        self.convert_objectids_in_query(item_dict)
        item_dict = self.convert_enums_in_query(item_dict)

        created_result = collection.insert_one(item_dict)
        inserted_id = created_result.inserted_id

        item_dict['id'] = str(inserted_id)
        item_dict.pop('_id', None)

        return item_dict

    async def put_item(self, model_name: str, item_id: str, update_fields: dict):
        collection = self.db[model_name]
        self.convert_objectids_in_query(update_fields)
        update_fields = self.convert_enums_in_query(update_fields)
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
    
    async def aggregate_items(self, model_name: str, pipeline: List[Dict[str, Any]]):
        collection = self.db[model_name]
        try:
            cursor = collection.aggregate(pipeline)
            # Fetch raw dicts, convert _id to id if present
            results = []
            for item in cursor:
                if '_id' in item:
                    item['id'] = str(item['_id'])
                    del item['_id']
                results.append(item)
            return results
        except Exception as e:
            import traceback
            traceback.print_exc()
            raise ValueError(f"Error en aggregate_items: {str(e)}")
    