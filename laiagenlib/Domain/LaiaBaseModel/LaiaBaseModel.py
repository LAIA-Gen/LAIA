from typing import Optional
from pydantic import BaseModel, ConfigDict
from pydantic import Field

class LaiaBaseModel(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    id: str = ""
    owner: Optional[str] = Field(None, description="The owner's ID")
