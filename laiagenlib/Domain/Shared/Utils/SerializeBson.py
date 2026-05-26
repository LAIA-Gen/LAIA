from bson import ObjectId

def serialize_bson(obj):
    if isinstance(obj, dict):
        result = {}
        for k, v in obj.items():
            if k == "_id":
                result["id"] = serialize_bson(v)
            else:
                result[k] = serialize_bson(v)
        return result
    elif isinstance(obj, list):
        return [serialize_bson(i) for i in obj]
    elif isinstance(obj, ObjectId):
        return str(obj)
    else:
        return obj