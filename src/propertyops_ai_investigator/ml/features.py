from pathlib import Path

import pandas as pd


RAW_DATA_PATH = Path("data/synthetic/sensor_readings.csv")
PROCESSED_DATA_PATH = Path("data/processed/telemetry_features.csv")


SENSOR_COLUMNS = {
    "AHU01-POWER": "power_kw",
    "AHU01-HEAT-VALVE": "heating_valve_pct",
    "AHU01-SUPPLY-TEMP": "supply_air_temp_c",
    "ZONE03-TEMP": "zone_temp_c",
    "AHU01-FAN": "fan_status",
}

CONTINUOUS_FEATURES = [
    "power_kw",
    "heating_valve_pct",
    "supply_air_temp_c",
    "zone_temp_c",
]

DISCRETE_FEATURES = [
    "fan_status",
]

def impute_missing_features(
    features: pd.DataFrame,
) -> pd.DataFrame:
    """Impute missing sensor values for ML processing."""

    result = features.copy()

    # Continuous telemetry:
    # interpolate between neighboring measurements.
    result[CONTINUOUS_FEATURES] = (
        result[CONTINUOUS_FEATURES]
        .interpolate(
            method="linear",
            limit_direction="both",
        )
    )

    # Discrete state such as fan on/off:
    # carry the last known state rather than creating
    # fractional values such as 0.5.
    result[DISCRETE_FEATURES] = (
        result[DISCRETE_FEATURES]
        .ffill()
        .bfill()
    )

    sensor_features = (
        CONTINUOUS_FEATURES
        + DISCRETE_FEATURES
    )

    remaining_missing = (
        result[sensor_features]
        .isna()
        .sum()
    )

    unresolved = remaining_missing[
        remaining_missing > 0
    ]

    if not unresolved.empty:
        raise ValueError(
            "Unable to impute all missing sensor values: "
            f"{unresolved.to_dict()}"
        )

    return result

def build_feature_table(df: pd.DataFrame) -> pd.DataFrame:
    features = (
        df.pivot(
            index="timestamp",
            columns="sensor_id",
            values="value",
        )
        .rename(columns=SENSOR_COLUMNS)
        .reset_index()
    )

    features["timestamp"] = pd.to_datetime(features["timestamp"])
    features = impute_missing_features(
        features
    )

    features["hour"] = features["timestamp"].dt.hour
    features["is_weekday"] = (
        features["timestamp"].dt.weekday < 5
    ).astype(int)

    features["expected_occupied"] = (
        (features["is_weekday"] == 1)
        & (features["hour"] >= 6)
        & (features["hour"] < 18)
    ).astype(int)

    return features


def create_feature_dataset() -> pd.DataFrame:
    raw = pd.read_csv(
        RAW_DATA_PATH,
        parse_dates=["timestamp"],
    )

    features = build_feature_table(raw)

    PROCESSED_DATA_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    features.to_csv(
        PROCESSED_DATA_PATH,
        index=False,
    )

    return features


if __name__ == "__main__":
    feature_df = create_feature_dataset()

    print(feature_df.head())
    print()
    print(f"Created {len(feature_df)} hourly feature rows.")
    print(f"Saved to: {PROCESSED_DATA_PATH}")