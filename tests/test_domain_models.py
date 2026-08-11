import pytest
from pydantic import ValidationError

from propertyops_ai_investigator.domain.models import (
    Building,
    Equipment,
    EquipmentType,
    Sensor,
    SensorType,
)


def test_building_requires_positive_area():
    with pytest.raises(ValidationError):
        Building(
            id="BLDG-001",
            name="Invalid Building",
            area_m2=-100,
        )


def test_create_ahu():
    equipment = Equipment(
        id="AHU-001",
        building_id="BLDG-001",
        zone_id=None,
        name="Main Air Handling Unit",
        equipment_type=EquipmentType.AHU,
    )

    assert equipment.equipment_type == EquipmentType.AHU


def test_create_temperature_sensor():
    sensor = Sensor(
        id="TEMP-001",
        zone_id="ZONE-001",
        equipment_id=None,
        sensor_type=SensorType.TEMPERATURE,
        unit="C",
    )

    assert sensor.sensor_type == SensorType.TEMPERATURE