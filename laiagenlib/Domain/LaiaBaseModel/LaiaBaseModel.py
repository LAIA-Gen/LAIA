from pydantic import BaseModel

class LaiaBaseModel(BaseModel):
    id: str = ""
    name: str

    def __init__(self, id, name):
        self.id = id
        self.name = name
