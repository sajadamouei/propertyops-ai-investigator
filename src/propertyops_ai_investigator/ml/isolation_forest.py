from pathlib import Path

import pandas as pd
from sklearn.ensemble import IsolationForest

from propertyops_ai_investigator.ml.features import (
    create_feature_dataset,
)


EVENT_COLUMNS = [
    "event_id",
    "start",
    "end",
    "points",
    "max_anomaly_score",
    "mean_anomaly_score",
]

TRAIN_END = pd.Timestamp("2026-01-14 23:00")

OUTPUT_PATH = Path(
    "data/processed/anomaly_scores.csv"
)

FEATURE_COLUMNS = [
    "power_kw",
    "heating_valve_pct",
    "supply_air_temp_c",
    "zone_temp_c",
    "fan_status",
    "expected_occupied",
]


def fit_detector(
    features: pd.DataFrame,
) -> tuple[IsolationForest, float]:
    training = features[
        features["timestamp"] <= TRAIN_END
    ]

    x_train = training[FEATURE_COLUMNS]

    model = IsolationForest(
        n_estimators=200,
        contamination="auto",
        random_state=42,
    )

    model.fit(x_train)

    # Higher value = more abnormal.
    training_scores = -model.score_samples(x_train)

    # Allow roughly the most unusual 1% of normal
    # training observations to define the boundary.
    threshold = pd.Series(training_scores).quantile(0.99)

    return model, float(threshold)


def score_anomalies(
    features: pd.DataFrame,
    model: IsolationForest,
    threshold: float,
) -> pd.DataFrame:
    scored = features.copy()

    x = scored[FEATURE_COLUMNS]

    scored["anomaly_score"] = -model.score_samples(x)

    scored["is_anomaly"] = (
        scored["anomaly_score"] > threshold
    )

    return scored


def build_events(
    scored: pd.DataFrame,
) -> pd.DataFrame:
    anomalies = (
        scored[scored["is_anomaly"]]
        .sort_values("timestamp")
        .copy()
    )

    if anomalies.empty:
        return pd.DataFrame(
            columns=EVENT_COLUMNS
        )

    time_gap = anomalies["timestamp"].diff()

    anomalies["new_event"] = (
        time_gap > pd.Timedelta(hours=1)
    )

    anomalies.loc[
        anomalies.index[0],
        "new_event",
    ] = True

    anomalies["event_id"] = (
        anomalies["new_event"].cumsum()
    )

    events = (
        anomalies.groupby("event_id")
        .agg(
            start=("timestamp", "min"),
            end=("timestamp", "max"),
            points=("timestamp", "size"),
            max_anomaly_score=(
                "anomaly_score",
                "max",
            ),
            mean_anomaly_score=(
                "anomaly_score",
                "mean",
            ),
        )
        .reset_index()
    )

    # Ignore isolated one-hour anomalies.
    events = events[
        events["points"] >= 2
    ]

    return events.reindex(
        columns=EVENT_COLUMNS
    )


if __name__ == "__main__":
    features = create_feature_dataset()

    model, threshold = fit_detector(features)

    scored = score_anomalies(
        features,
        model,
        threshold,
    )

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    scored.to_csv(
        OUTPUT_PATH,
        index=False,
    )

    print(
        f"Anomaly threshold: {threshold:.4f}"
    )

    print()
    print("Most unusual observations:")

    print(
        scored.sort_values(
            "anomaly_score",
            ascending=False,
        )[
            [
                "timestamp",
                "anomaly_score",
                "power_kw",
                "heating_valve_pct",
                "supply_air_temp_c",
                "zone_temp_c",
                "fan_status",
                "expected_occupied",
            ]
        ]
        .head(12)
        .to_string(index=False)
    )

    events = build_events(scored)

    print()
    print("Operational anomaly events:")
    print(events.to_string(index=False))