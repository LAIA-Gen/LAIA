from bson import ObjectId

def serialize_bson(obj):
    if isinstance(obj, dict):
        return {k: serialize_bson(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [serialize_bson(i) for i in obj]
    elif isinstance(obj, ObjectId):
        return str(obj)
    else:
        return obj