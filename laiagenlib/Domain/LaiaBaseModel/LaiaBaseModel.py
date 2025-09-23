from typing import Annotated, Optional
from pydantic import BaseModel
from pydantic import Field
from bson import ObjectId
from laiagenlib.Domain.Shared.Types.objectid_annotation import ObjectIdPydanticAnnotation

class LaiaBaseModel(BaseModel):
    id: str = ""
    owner: Optional[Annotated[ObjectId, ObjectIdPydanticAnnotation]] = None
    region: str = ""
