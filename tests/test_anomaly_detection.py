import pandas as pd

from propertyops_ai_investigator.ml.features import (
    create_feature_dataset,
)
from propertyops_ai_investigator.ml.isolation_forest import (
    build_events,
    fit_detector,
    score_anomalies,
)


def test_detector_finds_injected_incident():
    features = create_feature_dataset()

    model, threshold = fit_detector(features)

    scored = score_anomalies(
        features,
        model,
        threshold,
    )

    events = build_events(scored)

    expected_start = pd.Timestamp(
        "2026-01-15 01:00"
    )

    expected_end = pd.Timestamp(
        "2026-01-15 05:00"
    )

    matching = events[
        (events["start"] <= expected_start)
        & (events["end"] >= expected_end)
    ]

    assert len(matching) == 1