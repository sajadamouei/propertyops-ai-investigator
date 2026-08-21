import json

from propertyops_ai_investigator.data.experiment import (
    ScenarioType,
    create_scenario_config,
)
from propertyops_ai_investigator.services.pipeline import (
    PipelineService,
)
from propertyops_ai_investigator.services.rag_service import (
    RagService,
)
from propertyops_ai_investigator.services.workspace import (
    PipelineStep,
    load_manifest,
    reset_current_run,
)


def test_rag_service_retrieves_and_persists_results(
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

    PipelineService(
        workspace
    ).run_deterministic_pipeline()

    artifact = RagService(
        workspace
    ).run()

    assert len(artifact.results) == 3

    sources = {
        result.source
        for result in artifact.results
    }

    assert (
        "01_heating_valve_troubleshooting.md"
        in sources
    )

    assert (
        "02_after_hours_ahu_operation.md"
        in sources
    )

    path = (
        workspace
        / "rag_results.json"
    )

    assert path.exists()

    saved = json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )

    assert saved["query"]
    assert (
        len(
            saved["retrieval_queries"]
        )
        == 2
    )
    assert len(saved["results"]) == 3

    manifest = load_manifest(
        workspace
    )

    assert (
        PipelineStep.RAG
        in manifest.completed_steps
    )


def test_rag_service_requires_incident(
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

    PipelineService(
        workspace
    ).run_deterministic_pipeline()

    try:
        RagService(
            workspace
        ).run()

    except RuntimeError as exc:
        assert (
            "No operational incident"
            in str(exc)
        )

    else:
        raise AssertionError(
            "Expected RAG to require an incident."
        )


def test_default_rag_query_expresses_incident_relationships(
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

    incident = PipelineService(
        workspace
    ).run_deterministic_pipeline()

    assert incident is not None

    queries = RagService(
        workspace
    ).build_default_queries(
        incident
    )

    assert len(queries) == 2

    heating_query = (
        queries[0].lower()
    )

    operations_query = (
        queries[1].lower()
    )

    assert (
        "heating valve"
        in heating_query
    )

    assert (
        "supply-air"
        in heating_query
    )

    assert (
        "actuator"
        in heating_query
    )

    assert (
        "after-hours"
        in operations_query
    )

    assert (
        "schedule"
        in operations_query
    )

    assert (
        "override"
        in operations_query
    )