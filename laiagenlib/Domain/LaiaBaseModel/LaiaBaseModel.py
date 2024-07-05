from pydantic import BaseModel
from pydantic import Field

class LaiaBaseModel(BaseModel):
    id: str = ""
    name: str
    owner: str = ""
