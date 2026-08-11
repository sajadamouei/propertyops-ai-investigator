import pandas as pd

from propertyops_ai_investigator.ml.features import (
    create_feature_dataset,
)


TRAIN_END = pd.Timestamp("2026-01-14 23:00")


def detect_off_hours_power_anomalies(
    features: pd.DataFrame,
) -> pd.DataFrame:
    training = features[
        features["timestamp"] <= TRAIN_END
    ]

    normal_off_hours = training[
        training["expected_occupied"] == 0
    ]

    mean_power = normal_off_hours["power_kw"].mean()
    std_power = normal_off_hours["power_kw"].std()

    threshold = mean_power + 3 * std_power

    scored = features.copy()

    scored["baseline_anomaly"] = (
        (scored["expected_occupied"] == 0)
        & (scored["power_kw"] > threshold)
    )

    print(f"Normal off-hours mean: {mean_power:.2f} kW")
    print(f"Normal off-hours std:  {std_power:.2f} kW")
    print(f"3-sigma threshold:      {threshold:.2f} kW")

    return scored


if __name__ == "__main__":
    features = create_feature_dataset()

    scored = detect_off_hours_power_anomalies(features)

    anomalies = scored[
        scored["baseline_anomaly"]
    ]

    print()
    print("Detected anomalies:")
    print(
        anomalies[
            [
                "timestamp",
                "power_kw",
                "fan_status",
                "heating_valve_pct",
                "supply_air_temp_c",
            ]
        ].to_string(index=False)
    )