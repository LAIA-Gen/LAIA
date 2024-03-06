from typing import List, TypeVar, Type
from pydantic import BaseModel
import json

T = TypeVar('T', bound='BaseModel')

def individual_serial(item: T) -> dict:
    item['_id'] = str(item['_id'])
    item['id'] = str(item['_id'])
    del item['_id']
    return item

def list_serial(items: List[T]) -> list[dict]:
    return[individual_serial(item) for item in items]