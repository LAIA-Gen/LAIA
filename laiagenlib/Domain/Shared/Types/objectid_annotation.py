from bson import ObjectId
from pydantic_core import core_schema


class ObjectIdPydanticAnnotation:
    @classmethod
    def __get_pydantic_core_schema__(cls, source_type, handler):
        def validate_object_id(value):
            if isinstance(value, ObjectId):
                return value
            if isinstance(value, str) and ObjectId.is_valid(value):
                return ObjectId(value)
            raise ValueError("Invalid ObjectId")

        return core_schema.no_info_plain_validator_function(
            validate_object_id,
            serialization=core_schema.to_string_ser_schema(),
        )

    @classmethod
    def __get_pydantic_json_schema__(cls, core_schema, handler):
        return {
            "type": "string",
            "pattern": "^[0-9a-fA-F]{24}$",
            "examples": ["507f1f77bcf86cd799439011"],
        }
