from typing import Annotated, Optional
from pydantic import BaseModel
from pydantic import Field
from bson import ObjectId
from laiagenlib.Domain.Shared.Types.objectid_annotation import ObjectIdPydanticAnnotation

class LaiaBaseModel(BaseModel):
    id: str = ""
    owner: Optional[Annotated[ObjectId, ObjectIdPydanticAnnotation]] = None
    nicename: Optional[str] = None

    @classmethod
    def __get_pydantic_json_schema__(cls, core_schema, handler):
        json_schema = handler(core_schema)
        json_schema = handler.resolve_ref_schema(json_schema)
        extra = cls.model_config.get("json_schema_extra", {})
        excluded = extra.get("x-exclude-from-response", []) if isinstance(extra, dict) else []
        for field in excluded:
            json_schema.get("properties", {}).pop(field, None)
            required = json_schema.get("required", [])
            if field in required:
                required.remove(field)
        return json_schema