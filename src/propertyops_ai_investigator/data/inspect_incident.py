from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


DATA_PATH = Path("data/synthetic/sensor_readings.csv")


def load_data() -> pd.DataFrame:
    df = pd.read_csv(DATA_PATH, parse_dates=["timestamp"])
    return df


def plot_incident(df: pd.DataFrame) -> None:
    start = pd.Timestamp("2026-01-14 18:00")
    end = pd.Timestamp("2026-01-15 12:00")

    incident_df = df[
        (df["timestamp"] >= start)
        & (df["timestamp"] <= end)
    ]

    pivot = incident_df.pivot(
        index="timestamp",
        columns="sensor_id",
        values="value",
    )

    sensors = [
        "AHU01-POWER",
        "AHU01-HEAT-VALVE",
        "AHU01-SUPPLY-TEMP",
        "ZONE03-TEMP",
        "AHU01-FAN",
    ]

    for sensor in sensors:
        plt.figure(figsize=(10, 4))
        plt.plot(pivot.index, pivot[sensor], marker="o")
        plt.title(sensor)
        plt.xlabel("Time")
        plt.ylabel("Value")
        plt.xticks(rotation=45)
        plt.tight_layout()

        output = Path("data/synthetic") / f"{sensor.lower()}_incident.png"
        plt.savefig(output)
        plt.close()

        print(f"Created: {output}")


if __name__ == "__main__":
    data = load_data()
    plot_incident(data)