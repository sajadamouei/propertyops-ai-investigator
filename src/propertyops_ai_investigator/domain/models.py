from datetime import datetime

from pydantic import BaseModel, Field


class Building(BaseModel):
    id: str
    name: str
    area_m2: float = Field(gt=0)


class Zone(BaseModel):
    id: str
    building_id: str
    name: str
    floor: int


class SensorReading(BaseModel):
    sensor_id: str
    zone_id: str
    timestamp: datetime
    temperature_c: float | None = None
    energy_kw: float | None = None