from pydantic import BaseModel

class LaiaBaseModel(BaseModel):
    id: str = ""
    name: str
