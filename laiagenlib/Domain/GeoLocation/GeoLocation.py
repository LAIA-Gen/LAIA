from typing import Optional
from pydantic import Field
from ..LaiaBaseModel.LaiaBaseModel import LaiaBaseModel

class GeoLocation(LaiaBaseModel):
    address: str = Field(..., description="Dirección completa o término de búsqueda")
    lat: float = Field(..., description="Latitud")
    lon: float = Field(..., description="Longitud")
    geojson: Optional[dict] = Field(None, description="Estructura GeoJSON asociada a la ubicación")
