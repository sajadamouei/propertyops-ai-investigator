from datetime import datetime

import pytest
from pydantic import ValidationError

from propertyops_ai_investigator.data.experiment import (
    ExperimentConfig,
    FaultSpec,
    FaultType,
    ScenarioType,
    create_scenario_config,
)


def test_normal_scenario_has_no_faults():
    config = create_scenario_config(
        ScenarioType.NORMAL_OPERATION
    )

    assert config.days == 14
    assert config.seed == 42
    assert config.faults == []


def test_heating_valve_scenario_has_faults():
    config = create_scenario_config(
        ScenarioType.HEATING_VALVE_FAULT
    )

    sensor_ids = {
        fault.sensor_id
        for fault in config.faults
    }

    assert "AHU01-HEAT-VALVE" in sensor_ids
    assert "AHU01-POWER" in sensor_ids
    assert "AHU01-FAN" in sensor_ids


def test_non_missing_fault_requires_value():
    with pytest.raises(ValidationError):
        FaultSpec(
            sensor_id="AHU01-POWER",
            fault_type=FaultType.OFFSET,
            start=datetime(
                2026, 1, 15, 1
            ),
            end=datetime(
                2026, 1, 15, 5
            ),
        )


def test_missing_fault_does_not_require_value():
    fault = FaultSpec(
        sensor_id="AHU01-POWER",
        fault_type=FaultType.MISSING,
        start=datetime(
            2026, 1, 15, 1
        ),
        end=datetime(
            2026, 1, 15, 5
        ),
    )

    assert fault.value is None


def test_fault_end_must_follow_start():
    with pytest.raises(ValidationError):
        FaultSpec(
            sensor_id="AHU01-POWER",
            fault_type=FaultType.SPIKE,
            start=datetime(
                2026, 1, 15, 5
            ),
            end=datetime(
                2026, 1, 15, 1
            ),
            value=100,
        )