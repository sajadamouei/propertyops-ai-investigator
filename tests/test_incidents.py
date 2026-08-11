from propertyops_ai_investigator.domain.models import (
    IncidentSeverity,
)
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


def test_anomaly_becomes_operational_incident():
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

    assert len(incidents) == 1

    incident = incidents[0]

    assert incident.building_id == "BLDG-001"
    assert incident.equipment_id == "AHU-001"
    assert incident.severity == IncidentSeverity.HIGH
    assert len(incident.evidence) == 4