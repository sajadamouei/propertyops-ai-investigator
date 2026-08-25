from fastapi.testclient import TestClient

import propertyops_ai_investigator.api.main as api_main

from propertyops_ai_investigator.api.main import app
from propertyops_ai_investigator.data.experiment import (
    ScenarioType,
    create_scenario_config,
)
from propertyops_ai_investigator.domain.models import (
    ApprovalRecord,
    InvestigationAssessment,
    OperationalInvestigation,
    WorkOrder,
    WorkOrderCreationResult,
    WorkOrderStatus,
)
from propertyops_ai_investigator.rag.retriever import (
    RetrievalResult,
)
from propertyops_ai_investigator.services.investigation_service import (
    ToolTraceEntry,
)
from propertyops_ai_investigator.services.pipeline import (
    PipelineService,
)
from propertyops_ai_investigator.services.rag_service import (
    RagArtifact,
)
from propertyops_ai_investigator.services.workspace import (
    APPROVAL_FILE,
    ASSESSMENT_FILE,
    INVESTIGATION_FILE,
    MCP_TRACE_FILE,
    RAG_RESULTS_FILE,
    WORK_ORDER_FILE,
    PipelineStep,
    RunStatus,
    load_manifest,
    reset_current_run,
    save_manifest,
)


def configure_recovery_workspace(
    monkeypatch,
    tmp_path,
):
    workspace_dir = tmp_path / "current_run"
    monkeypatch.setattr(
        api_main,
        "CURRENT_RUN_DIR",
        workspace_dir,
    )
    monkeypatch.setattr(
        api_main,
        "CHECKPOINT_DB_PATH",
        tmp_path / "checkpoints.sqlite",
    )
    return workspace_dir


def test_recovery_returns_404_without_current_run(
    tmp_path,
    monkeypatch,
):
    configure_recovery_workspace(
        monkeypatch,
        tmp_path,
    )

    with TestClient(app) as client:
        response = client.get(
            "/api/runs/current/recovery"
        )

    assert response.status_code == 404
    assert response.json() == {
        "detail": "No current run exists."
    }


def test_recovery_snapshot_survives_api_restart_and_covers_decisions(
    tmp_path,
    monkeypatch,
):
    workspace_dir = configure_recovery_workspace(
        monkeypatch,
        tmp_path,
    )
    config = create_scenario_config(
        ScenarioType.HEATING_VALVE_FAULT,
        days=14,
        seed=42,
    )
    reset_current_run(
        config,
        workspace_dir,
    )
    incident = PipelineService(
        workspace_dir
    ).run_deterministic_pipeline()
    assert incident is not None

    investigation = OperationalInvestigation(
        summary="Evidence gathered.",
        telemetry_findings=[
            "Heating valve remained open."
        ],
        maintenance_findings=[
            "Actuator was previously calibrated."
        ],
        occupant_impact=[
            "Cold comfort complaints were reported."
        ],
        evidence=[
            "Persisted operational evidence."
        ],
    )
    rag = RagArtifact(
        query="heating valve troubleshooting",
        retrieval_queries=[
            "heating valve troubleshooting"
        ],
        k=1,
        embedding_model="test-model",
        results=[
            RetrievalResult(
                chunk_id="chunk-1",
                source="guide.md",
                text="Inspect the actuator linkage.",
                score=0.9,
            )
        ],
    )
    assessment = InvestigationAssessment(
        likely_issue="Possible actuator fault.",
        confidence=0.82,
        telemetry_findings=[
            "Heating valve remained open."
        ],
        maintenance_findings=[
            "Prior calibration exists."
        ],
        occupant_impact=[
            "Cold comfort complaints."
        ],
        evidence=[
            "Combined persisted evidence."
        ],
        recommended_next_step=(
            "Inspect the actuator and linkage."
        ),
    )
    trace = ToolTraceEntry(
        event="tool_call",
        tool_name="get_equipment_sensors",
        tool_call_id="call-1",
        arguments={
            "equipment_id": incident.equipment_id,
        },
    )

    (
        workspace_dir
        / INVESTIGATION_FILE
    ).write_text(
        investigation.model_dump_json(
            indent=2
        ),
        encoding="utf-8",
    )
    (
        workspace_dir
        / RAG_RESULTS_FILE
    ).write_text(
        rag.model_dump_json(indent=2),
        encoding="utf-8",
    )
    (
        workspace_dir
        / ASSESSMENT_FILE
    ).write_text(
        assessment.model_dump_json(
            indent=2
        ),
        encoding="utf-8",
    )
    (
        workspace_dir
        / MCP_TRACE_FILE
    ).write_text(
        trace.model_dump_json(),
        encoding="utf-8",
    )

    manifest = load_manifest(
        workspace_dir
    )
    manifest.completed_steps.extend(
        [
            PipelineStep.AI_INVESTIGATION,
            PipelineStep.RAG,
            PipelineStep.ASSESSMENT,
        ]
    )
    manifest.status = RunStatus.WAITING
    manifest.current_step = (
        PipelineStep.HUMAN_APPROVAL
    )
    save_manifest(
        manifest,
        workspace_dir,
    )

    with TestClient(app) as first_client:
        waiting_response = first_client.get(
            "/api/runs/current/recovery"
        )

    assert waiting_response.status_code == 200
    waiting = waiting_response.json()
    assert waiting["manifest"]["status"] == "waiting"
    assert waiting["incident_stage"]["incident"]["id"] == incident.id
    assert waiting["investigation"]["summary"] == "Evidence gathered."
    assert waiting["rag"]["results"][0]["chunk_id"] == "chunk-1"
    assert waiting["assessment"]["confidence"] == 0.82
    assert waiting["approval_request"]["incident_id"] == incident.id

    # A new TestClient lifespan reopens the persistent SQLite checkpointer,
    # mirroring a FastAPI process restart for the recovery read model.
    with TestClient(app) as restarted_client:
        restarted_response = restarted_client.get(
            "/api/runs/current/recovery"
        )

    assert restarted_response.status_code == 200
    assert restarted_response.json()["approval_request"] == waiting[
        "approval_request"
    ]

    approval = ApprovalRecord(
        approved=False,
        rationale="Need more evidence.",
    )
    (
        workspace_dir
        / APPROVAL_FILE
    ).write_text(
        approval.model_dump_json(indent=2),
        encoding="utf-8",
    )
    manifest = load_manifest(
        workspace_dir
    )
    manifest.completed_steps.append(
        PipelineStep.HUMAN_APPROVAL
    )
    manifest.status = RunStatus.COMPLETE
    manifest.current_step = None
    save_manifest(
        manifest,
        workspace_dir,
    )

    with TestClient(app) as client:
        rejected = client.get(
            "/api/runs/current/recovery"
        ).json()

    assert rejected["approval"]["approved"] is False
    assert rejected["approval_request"] is None
    assert rejected["work_order"] is None

    approval = ApprovalRecord(
        approved=True,
        rationale="Approved.",
    )
    work_order = WorkOrderCreationResult(
        created=True,
        work_order=WorkOrder(
            id="WO-RECOVERY",
            building_id=incident.building_id,
            equipment_id=incident.equipment_id,
            created_at="2026-01-15T12:00:00Z",
            description="Inspect actuator and linkage.",
            status=WorkOrderStatus.OPEN,
        ),
    )
    (
        workspace_dir
        / APPROVAL_FILE
    ).write_text(
        approval.model_dump_json(indent=2),
        encoding="utf-8",
    )
    (
        workspace_dir
        / WORK_ORDER_FILE
    ).write_text(
        work_order.model_dump_json(indent=2),
        encoding="utf-8",
    )
    manifest = load_manifest(
        workspace_dir
    )
    manifest.completed_steps.append(
        PipelineStep.WORK_ORDER
    )
    save_manifest(
        manifest,
        workspace_dir,
    )

    with TestClient(app) as client:
        approved = client.get(
            "/api/runs/current/recovery"
        ).json()

    assert approved["approval"]["approved"] is True
    assert approved["work_order"]["work_order"]["id"] == "WO-RECOVERY"


def test_recovery_snapshot_supports_completed_normal_run(
    tmp_path,
    monkeypatch,
):
    workspace_dir = configure_recovery_workspace(
        monkeypatch,
        tmp_path,
    )
    config = create_scenario_config(
        ScenarioType.NORMAL_OPERATION,
        days=14,
        seed=42,
    )
    reset_current_run(
        config,
        workspace_dir,
    )
    incident = PipelineService(
        workspace_dir
    ).run_deterministic_pipeline()
    assert incident is None

    with TestClient(app) as client:
        response = client.get(
            "/api/runs/current/recovery"
        )

    assert response.status_code == 200
    recovery = response.json()
    assert recovery["manifest"]["config"]["scenario"] == "normal_operation"
    assert recovery["incident_stage"]["incident"] is None
    assert recovery["detection_stage"]["event_count"] == 0
    assert recovery["approval"] is None
    assert recovery["work_order"] is None
