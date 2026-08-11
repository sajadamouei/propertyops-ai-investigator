from propertyops_ai_investigator.ml.features import (
    create_feature_dataset,
)
from propertyops_ai_investigator.ml.incidents import (
    create_operational_incidents,
)
from propertyops_ai_investigator.ml.isolation_forest import (
    build_events,
    fit_detector,
    score_anomalies,
)


def main() -> None:
    features = create_feature_dataset()

    model, threshold = fit_detector(features)

    scored = score_anomalies(
        features,
        model,
        threshold,
    )

    events = build_events(scored)

    incidents = create_operational_incidents(
        scored,
        events,
    )

    for incident in incidents:
        print(
            incident.model_dump_json(
                indent=2,
            )
        )


if __name__ == "__main__":
    main()