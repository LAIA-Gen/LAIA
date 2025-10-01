from typing import List
from pydantic import Field
from laiagenlib.Domain.LaiaBaseModel.LaiaBaseModel import LaiaBaseModel
from pydantic import ConfigDict

class Shard(LaiaBaseModel):
    key: str = Field(...,
        description="Nombre del campo en los modelos (por ejemplo 'region')",
        x_frontend_fieldName="Key",
        x_frontend_fieldDescription="Campo shard en los modelos",
        x_frontend_editable=True,
        x_frontend_placeholder="Nombre del campo shard"
    )
    name: str = Field(...,
        description="Texto que se mostrará en la UI para este shard",
        x_frontend_fieldName="Name",
        x_frontend_fieldDescription="Nombre visible en la UI",
        x_frontend_editable=True,
        x_frontend_placeholder="Nombre visible"
    )
    values: List[str] = Field(...,
        description="Lista de valores válidos para este shard",
        x_frontend_fieldName="Values",
        x_frontend_fieldDescription="Valores disponibles",
        x_frontend_editable=True,
        x_frontend_placeholder="Lista de valores"
    )