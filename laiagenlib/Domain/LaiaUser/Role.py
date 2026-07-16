from pydantic import ConfigDict
from ..LaiaBaseModel.LaiaBaseModel import LaiaBaseModel

class Role(LaiaBaseModel):
    name: str

    model_config = ConfigDict(
        json_schema_extra={
            "x-frontend-defaultFields": ["id", "name"]
        }
    )
