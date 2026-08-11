from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class EquipmentType(str, Enum):
    AHU = "ahu"
    HEAT_PUMP = "heat_pump"


class SensorType(str, Enum):
    TEMPERATURE = "temperature"
    ENERGY_POWER = "energy_power"
    FAN_STATUS = "fan_status"
    VALVE_POSITION = "valve_position"


class WorkOrderStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    CLOSED = "closed"


class Building(BaseModel):
    id: str
    name: str
    area_m2: float = Field(gt=0)


class Zone(BaseModel):
    id: str
    building_id: str
    name: str
    floor: int


class Equipment(BaseModel):
    id: str
    building_id: str
    zone_id: str | None = None
    name: str
    equipment_type: EquipmentType


class Sensor(BaseModel):
    id: str
    equipment_id: str | None = None
    zone_id: str | None = None
    sensor_type: SensorType
    unit: str


class SensorReading(BaseModel):
    sensor_id: str
    timestamp: datetime
    value: float


class TenantComplaint(BaseModel):
    id: str
    building_id: str
    zone_id: str
    timestamp: datetime
    category: str
    description: str


class WorkOrder(BaseModel):
    id: str
    building_id: str
    equipment_id: str | None = None
    created_at: datetime
    description: str
    status: WorkOrderStatus

class IncidentSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TelemetryEvidence(BaseModel):
    metric: str
    value: float
    unit: str | None = None
    aggregation: str


class OperationalIncident(BaseModel):
    id: str
    building_id: str
    equipment_id: str
    started_at: datetime
    ended_at: datetime
    severity: IncidentSeverity
    anomaly_score: float
    summary: str
    evidence: list[TelemetryEvidence]