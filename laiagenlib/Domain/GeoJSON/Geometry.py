from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field

class Type(Enum):
    Point = 'Point'
    LineString = 'LineString'
    Polygon = 'Polygon'
    MultiPoint = 'MultiPoint'
    MultiLineString = 'MultiLineString'
    MultiPolygon = 'MultiPolygon'

class Geometry(BaseModel):
    type: Type = Field(..., description='the geometry type', )

class Feature(BaseModel):
    type: str = Field('Feature', description='the feature type', )
    properties: dict = Field({}, )

class GeometryLineString(Geometry):
    coordinates: Optional[List[List[float]]] = Field(None, title='Coordinates', )

class LineString(Feature):
    geometry: GeometryLineString = Field()

class GeometryMultiLineString(Geometry):
    coordinates: Optional[List[List[List[float]]]] = Field(None, title='Coordinates', )

class MultiLineString(Feature):
    geometry: GeometryMultiLineString = Field()

class GeometryMultiPoint(Geometry):
    coordinates: Optional[List[List[float]]] = Field(None, title='Coordinates', )

class MultiPoint(Feature):
    geometry: GeometryMultiPoint = Field()

class GeometryMultiPolygon(Geometry):
    coordinates: Optional[List[List[List[List[float]]]]] = Field(
        None, title='Coordinates'
    )

class MultiPolygon(Feature):
    geometry: GeometryMultiPolygon = Field()

class GeometryPoint(Geometry):
    coordinates: Optional[List[float]] = Field(
        None, description='Point in 3D space', title='Coordinates'
    )

class Point(Feature):
    geometry: GeometryPoint = Field()

class GeometryPolygon(Geometry):
    coordinates: Optional[List[List[List[float]]]] = Field(None, title='Coordinates', )

class Polygon(Feature):
    geometry: GeometryPolygon = Field()
