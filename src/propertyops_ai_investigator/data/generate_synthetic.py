from pathlib import Path

import numpy as np
import pandas as pd


RANDOM_SEED = 42


def generate_sensor_readings() -> pd.DataFrame:
    rng = np.random.default_rng(RANDOM_SEED)

    timestamps = pd.date_range(
        start="2026-01-05 00:00",
        end="2026-01-18 23:00",
        freq="h",
    )

    rows = []

    for timestamp in timestamps:
        weekday = timestamp.weekday() < 5
        occupied = weekday and 6 <= timestamp.hour < 18

        # Normal operating behaviour
        fan_status = 1.0 if occupied else 0.0

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

        # Inject our incident.
        incident = (
            pd.Timestamp("2026-01-15 01:00")
            <= timestamp
            <= pd.Timestamp("2026-01-15 05:00")
        )

        if incident:
            fan_status = 1.0
            energy_kw = rng.normal(145, 4)
            heating_valve = rng.normal(92, 3)
            supply_air_temp = rng.normal(14.5, 0.3)

        # Cold building after the incident.
        if pd.Timestamp("2026-01-15 06:00") <= timestamp <= pd.Timestamp(
            "2026-01-15 10:00"
        ):
            zone_temp = rng.normal(18.3, 0.3)

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
                    "value": round(float(value), 2),
                }
            )

    return pd.DataFrame(rows)


def save_sensor_readings(output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / "sensor_readings.csv"

    readings = generate_sensor_readings()
    readings.to_csv(output_path, index=False)

    return output_path


if __name__ == "__main__":
    path = save_sensor_readings(Path("data/synthetic"))

    print(f"Created synthetic sensor data: {path}")