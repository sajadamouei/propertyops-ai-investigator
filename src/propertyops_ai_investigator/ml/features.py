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