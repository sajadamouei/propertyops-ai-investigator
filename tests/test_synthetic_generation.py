import pandas as pd

from propertyops_ai_investigator.data.experiment import (
    FaultSpec,
    FaultType,
    ScenarioType,
    create_scenario_config,
)
from propertyops_ai_investigator.data.generate_synthetic import (
    apply_faults,
    generate_base_telemetry,
    generate_sensor_readings,
)


def test_normal_generation_has_expected_shape():
    config = create_scenario_config(
        ScenarioType.NORMAL_OPERATION
    )

    readings = generate_sensor_readings(
        config
    )

    assert len(readings) == 14 * 24 * 5

    assert set(
        readings["sensor_id"].unique()
    ) == {
        "AHU01-FAN",
        "AHU01-POWER",
        "AHU01-HEAT-VALVE",
        "AHU01-SUPPLY-TEMP",
        "ZONE03-TEMP",
    }


def test_generation_is_deterministic_for_seed():
    config = create_scenario_config(
        ScenarioType.NORMAL_OPERATION,
        seed=42,
    )

    first = generate_sensor_readings(
        config
    )

    second = generate_sensor_readings(
        config
    )

    pd.testing.assert_frame_equal(
        first,
        second,
    )


def test_heating_fault_changes_incident_window():
    normal_config = create_scenario_config(
        ScenarioType.NORMAL_OPERATION
    )

    fault_config = create_scenario_config(
        ScenarioType.HEATING_VALVE_FAULT
    )

    normal = generate_sensor_readings(
        normal_config
    )

    faulty = generate_sensor_readings(
        fault_config
    )

    timestamp = pd.Timestamp(
        "2026-01-15 02:00"
    )

    normal_power = normal[
        (normal["sensor_id"] == "AHU01-POWER")
        & (normal["timestamp"] == timestamp)
    ]["value"].iloc[0]

    faulty_power = faulty[
        (faulty["sensor_id"] == "AHU01-POWER")
        & (faulty["timestamp"] == timestamp)
    ]["value"].iloc[0]

    assert faulty_power > normal_power + 100


def test_missing_fault_creates_missing_values():
    config = create_scenario_config(
        ScenarioType.NORMAL_OPERATION
    )

    base = generate_base_telemetry(
        config
    )

    fault = FaultSpec(
        sensor_id="AHU01-POWER",
        fault_type=FaultType.MISSING,
        start=pd.Timestamp(
            "2026-01-15 01:00"
        ),
        end=pd.Timestamp(
            "2026-01-15 03:00"
        ),
    )

    faulty = apply_faults(
        base,
        [fault],
    )

    missing = faulty[
        (faulty["sensor_id"] == "AHU01-POWER")
        & (
            faulty["timestamp"]
            >= pd.Timestamp(
                "2026-01-15 01:00"
            )
        )
        & (
            faulty["timestamp"]
            <= pd.Timestamp(
                "2026-01-15 03:00"
            )
        )
    ]

    assert missing["value"].isna().all()