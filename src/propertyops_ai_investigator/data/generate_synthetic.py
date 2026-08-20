from pathlib import Path

import numpy as np
import pandas as pd

from propertyops_ai_investigator.data.experiment import (
    ExperimentConfig,
    FaultSpec,
    FaultType,
    ScenarioType,
    create_scenario_config,
)


SENSOR_IDS = {
    "AHU01-FAN",
    "AHU01-POWER",
    "AHU01-HEAT-VALVE",
    "AHU01-SUPPLY-TEMP",
    "ZONE03-TEMP",
}


def generate_base_telemetry(
    config: ExperimentConfig,
) -> pd.DataFrame:
    """Generate normal building telemetry without injected faults."""

    rng = np.random.default_rng(config.seed)

    timestamps = pd.date_range(
        start=config.start_at,
        periods=config.days * 24,
        freq="h",
    )

    rows = []

    for timestamp in timestamps:
        weekday = timestamp.weekday() < 5
        occupied = (
            weekday
            and 6 <= timestamp.hour < 18
        )

        fan_status = (
            1.0 if occupied else 0.0
        )

        energy_kw = (
            rng.normal(115, 7)
            if occupied
            else rng.normal(28, 3)
        )

        heating_valve = (
            rng.normal(35, 8)
            if occupied
            else rng.normal(5, 2)
        )

        supply_air_temp = (
            rng.normal(19.0, 0.5)
            if occupied
            else rng.normal(17.0, 0.4)
        )

        zone_temp = (
            rng.normal(21.2, 0.4)
            if occupied
            else rng.normal(19.8, 0.5)
        )

        sensor_values = {
            "AHU01-FAN": fan_status,
            "AHU01-POWER": energy_kw,
            "AHU01-HEAT-VALVE": heating_valve,
            "AHU01-SUPPLY-TEMP": supply_air_temp,
            "ZONE03-TEMP": zone_temp,
        }

        for sensor_id, value in sensor_values.items():
            rows.append(
                {
                    "sensor_id": sensor_id,
                    "timestamp": timestamp,
                    "value": round(
                        float(value),
                        2,
                    ),
                }
            )

    return pd.DataFrame(rows)


def apply_fault(
    readings: pd.DataFrame,
    fault: FaultSpec,
) -> None:
    """Apply one fault to a telemetry DataFrame in place."""

    if fault.sensor_id not in SENSOR_IDS:
        raise ValueError(
            f"Unknown sensor ID: {fault.sensor_id}"
        )

    mask = (
        (readings["sensor_id"] == fault.sensor_id)
        & (readings["timestamp"] >= fault.start)
        & (readings["timestamp"] <= fault.end)
    )

    if not mask.any():
        raise ValueError(
            "Fault does not overlap generated telemetry: "
            f"{fault.sensor_id} "
            f"{fault.start.isoformat()} - "
            f"{fault.end.isoformat()}"
        )

    if fault.fault_type == FaultType.MISSING:
        readings.loc[mask, "value"] = np.nan
        return

    value = fault.value

    if value is None:
        raise ValueError(
            f"{fault.fault_type.value} requires a value."
        )

    if fault.fault_type == FaultType.STUCK:
        readings.loc[mask, "value"] = value

    elif fault.fault_type == FaultType.OFFSET:
        readings.loc[mask, "value"] += value

    elif fault.fault_type == FaultType.MULTIPLIER:
        readings.loc[mask, "value"] *= value

    elif fault.fault_type == FaultType.SPIKE:
        matching_indexes = readings.index[mask]

        spike_index = matching_indexes[
            len(matching_indexes) // 2
        ]

        readings.loc[
            spike_index,
            "value",
        ] += value

    else:
        raise ValueError(
            f"Unsupported fault type: {fault.fault_type}"
        )


def apply_faults(
    readings: pd.DataFrame,
    faults: list[FaultSpec],
) -> pd.DataFrame:
    """Return telemetry with all configured faults applied."""

    result = readings.copy()

    for fault in faults:
        apply_fault(
            result,
            fault,
        )

    result["value"] = result["value"].round(2)

    return result


def generate_sensor_readings(
    config: ExperimentConfig | None = None,
) -> pd.DataFrame:
    """Generate telemetry for an experiment scenario."""

    if config is None:
        config = create_scenario_config(
            ScenarioType.HEATING_VALVE_FAULT
        )

    base = generate_base_telemetry(
        config
    )

    return apply_faults(
        base,
        config.faults,
    )


def save_sensor_readings(
    output_dir: Path,
    config: ExperimentConfig | None = None,
) -> Path:
    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path = (
        output_dir / "sensor_readings.csv"
    )

    readings = generate_sensor_readings(
        config
    )

    readings.to_csv(
        output_path,
        index=False,
    )

    return output_path


if __name__ == "__main__":
    config = create_scenario_config(
        ScenarioType.HEATING_VALVE_FAULT
    )

    path = save_sensor_readings(
        Path("data/synthetic"),
        config,
    )

    print(
        f"Created synthetic sensor data: {path}"
    )
    print(
        f"Scenario: {config.scenario.value}"
    )