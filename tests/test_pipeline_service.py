import json

import pandas as pd

from propertyops_ai_investigator.data.experiment import (
    ScenarioType,
    create_scenario_config,
)
from propertyops_ai_investigator.services.pipeline import (
    PipelineService,
)
from propertyops_ai_investigator.services.workspace import (
    PipelineStep,
    load_manifest,
    reset_current_run,
)


def test_heating_fault_pipeline_creates_incident(
    tmp_path,
):
    workspace = (
        tmp_path / "current_run"
    )

    config = create_scenario_config(
        ScenarioType.HEATING_VALVE_FAULT
    )

    reset_current_run(
        config,
        workspace,
    )

    service = PipelineService(
        workspace
    )

    incident = (
        service.run_deterministic_pipeline()
    )

    assert incident is not None

    assert (
        incident.building_id
        == "BLDG-001"
    )

    assert (
        incident.equipment_id
        == "AHU-001"
    )

    assert (
        pd.Timestamp(
            incident.started_at
        )
        == pd.Timestamp(
            "2026-01-15 01:00"
        )
    )

    assert (
        pd.Timestamp(
            incident.ended_at
        )
        == pd.Timestamp(
            "2026-01-15 05:00"
        )
    )

    assert (
        workspace
        / "raw_telemetry.csv"
    ).exists()

    assert (
        workspace
        / "features.csv"
    ).exists()

    assert (
        workspace
        / "anomaly_scores.csv"
    ).exists()

    assert (
        workspace
        / "events.csv"
    ).exists()

    assert (
        workspace
        / "detection.json"
    ).exists()

    assert (
        workspace
        / "incident.json"
    ).exists()

    manifest = load_manifest(
        workspace
    )

    assert manifest.completed_steps == [
        PipelineStep.GENERATE_DATA,
        PipelineStep.FEATURE_ENGINEERING,
        PipelineStep.ANOMALY_DETECTION,
        PipelineStep.BUILD_INCIDENT,
    ]


def test_normal_pipeline_creates_no_incident(
    tmp_path,
):
    workspace = (
        tmp_path / "current_run"
    )

    config = create_scenario_config(
        ScenarioType.NORMAL_OPERATION
    )

    reset_current_run(
        config,
        workspace,
    )

    service = PipelineService(
        workspace
    )

    incident = (
        service.run_deterministic_pipeline()
    )

    assert incident is None

    events = pd.read_csv(
        workspace / "events.csv"
    )

    assert events.empty

    incident_data = json.loads(
        (
            workspace
            / "incident.json"
        ).read_text(
            encoding="utf-8"
        )
    )

    assert incident_data is None


def test_pipeline_requires_previous_stage(
    tmp_path,
):
    workspace = (
        tmp_path / "current_run"
    )

    config = create_scenario_config(
        ScenarioType.NORMAL_OPERATION
    )

    reset_current_run(
        config,
        workspace,
    )

    service = PipelineService(
        workspace
    )

    try:
        service.engineer_features()
    except RuntimeError as exc:
        assert (
            "raw_telemetry.csv"
            in str(exc)
        )
    else:
        raise AssertionError(
            "Expected missing artifact error."
        )