from typing import List, Optional
from pydantic import BaseModel, Field

from ..LaiaBaseModel.LaiaBaseModel import LaiaBaseModel

class LaiaUser(LaiaBaseModel):
    email: str
    password: str
    roles: List[str] = Field([], x_frontend_relation="Role")
    nicename: Optional[str] = None
    shard: Optional[str] = Field(
        None,
        description="Shard o región asignada a este usuario",
        x_frontend_fieldName="Shard",
        x_frontend_fieldDescription="Región asignada al usuario",
        x_frontend_editable=True,
        x_frontend_placeholder="Introduce la región"
    )
