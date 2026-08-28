import json

import pytest
from fastapi.testclient import TestClient

from propertyops_ai_investigator.api.main import (
    app,
)

from types import SimpleNamespace

import propertyops_ai_investigator.api.main as api_main

from propertyops_ai_investigator.domain.models import (
    ApprovalRecord,
    InvestigationAssessment,
    OperationalInvestigation,
    WorkOrder,
    WorkOrderCreationResult,
    WorkOrderStatus,
)

from propertyops_ai_investigator.services.investigation_service import (
    ToolTraceEntry,
)

from propertyops_ai_investigator.services.investigation_service import (
    ToolTraceEntry,
)
from propertyops_ai_investigator.services.rag_service import (
    RagArtifact,
)
from propertyops_ai_investigator.services.workspace import (
    PipelineStep,
    RunStatus,
    load_manifest,
    save_manifest,
    APPROVAL_FILE,
    ASSESSMENT_FILE,
    CURRENT_RUN_DIR,
    INVESTIGATION_FILE,
    MCP_TRACE_FILE,
    WORK_ORDER_FILE,
)


@pytest.fixture
def client(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(
        api_main,
        "CHECKPOINT_DB_PATH",
        tmp_path / "checkpoints.sqlite",
    )

    with TestClient(app) as test_client:
        yield test_client


def heating_fault_payload() -> dict:
    return {
        "scenario": "heating_valve_fault",
        "days": 14,
        "seed": 42,
    }


def test_health(client):
    response = client.get(
        "/api/health"
    )

    assert response.status_code == 200

    assert response.json() == {
        "status": "ok"
    }


def test_heating_fault_pipeline_through_api(
    client,
):
    response = client.post(
        "/api/runs/reset",
        json=heating_fault_payload(),
    )

    assert response.status_code == 200

    assert (
        client.post(
            "/api/pipeline/generate"
        ).status_code
        == 200
    )

    assert (
        client.post(
            "/api/pipeline/features"
        ).status_code
        == 200
    )

    detection = client.post(
        "/api/pipeline/detect"
    )

    assert detection.status_code == 200

    detection_data = detection.json()

    assert (
        detection_data[
            "event_count"
        ]
        == 1
    )

    incident = client.post(
        "/api/pipeline/incident"
    )

    assert incident.status_code == 200

    incident_data = (
        incident.json()["incident"]
    )

    assert incident_data is not None

    assert (
        incident_data["equipment_id"]
        == "AHU-001"
    )


def test_artifact_endpoint_returns_rows(
    client,
):
    reset_response = client.post(
        "/api/runs/reset",
        json=heating_fault_payload(),
    )

    assert reset_response.status_code == 200

    generate_response = client.post(
        "/api/pipeline/generate"
    )

    assert generate_response.status_code == 200

    response = client.get(
        "/api/artifacts/raw-telemetry",
        params={
            "limit": 5,
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["total_rows"] == 1680
    assert len(data["rows"]) == 5


def test_pipeline_rejects_out_of_order_step(
    client,
):
    reset_response = client.post(
        "/api/runs/reset",
        json={
            "scenario": "normal_operation",
            "days": 14,
            "seed": 42,
        },
    )

    assert reset_response.status_code == 200

    response = client.post(
        "/api/pipeline/features"
    )

    assert response.status_code == 400

    assert (
        "raw_telemetry.csv"
        in response.json()["detail"]
    )

def test_rag_pipeline_through_api(
    client,
):
    response = client.post(
        "/api/runs/reset",
        json={
            "scenario": "heating_valve_fault",
            "days": 14,
            "seed": 42,
        },
    )

    assert response.status_code == 200

    assert (
        client.post(
            "/api/pipeline/generate"
        ).status_code
        == 200
    )

    assert (
        client.post(
            "/api/pipeline/features"
        ).status_code
        == 200
    )

    assert (
        client.post(
            "/api/pipeline/detect"
        ).status_code
        == 200
    )

    assert (
        client.post(
            "/api/pipeline/incident"
        ).status_code
        == 200
    )

    rag = client.post(
        "/api/pipeline/rag",
        json={
            "k": 3,
        },
    )

    assert rag.status_code == 200

    data = rag.json()

    assert (
        len(
            data["retrieval_queries"]
        )
        == 2
    )

    assert len(
        data["results"]
    ) == 3

    sources = {
        result["source"]
        for result in data["results"]
    }

    assert (
        "01_heating_valve_troubleshooting.md"
        in sources
    )

    assert (
        "02_after_hours_ahu_operation.md"
        in sources
    )

    artifact = client.get(
        "/api/artifacts/rag"
    )

    assert artifact.status_code == 200

def test_workflow_start_and_reject_through_api(
    client,
    monkeypatch,
):
    reset = client.post(
        "/api/runs/reset",
        json=heating_fault_payload(),
    )

    assert reset.status_code == 200

    investigation = (
        OperationalInvestigation(
            summary=(
                "Operational evidence "
                "gathered."
            ),
            telemetry_findings=[
                "High valve command."
            ],
            maintenance_findings=[
                "Previous calibration."
            ],
            occupant_impact=[
                "Cold complaints."
            ],
            evidence=[
                "MCP evidence."
            ],
        )
    )

    rag = RagArtifact(
        query="test query",
        retrieval_queries=[
            "test query"
        ],
        k=1,
        embedding_model="test-model",
        results=[],
    )

    assessment = (
        InvestigationAssessment(
            likely_issue=(
                "Possible heating valve "
                "mechanical issue."
            ),
            confidence=0.8,
            telemetry_findings=[
                "High valve command."
            ],
            maintenance_findings=[
                "Previous calibration."
            ],
            occupant_impact=[
                "Cold complaints."
            ],
            evidence=[
                "Combined evidence."
            ],
            recommended_next_step=(
                "Inspect actuator."
            ),
        )
    )

    async def fake_start(
        workspace_dir,
        checkpointer,
    ):
        assert workspace_dir == CURRENT_RUN_DIR
        assert checkpointer is (
            app.state.workflow_checkpointer
        )

        manifest = load_manifest()

        manifest.status = (
            RunStatus.WAITING
        )
        manifest.current_step = (
            PipelineStep.HUMAN_APPROVAL
        )

        save_manifest(
            manifest
        )

        return {
            "investigation": (
                investigation
            ),
            "mcp_trace": [],
            "rag": rag,
            "assessment": assessment,
            "__interrupt__": [
                SimpleNamespace(
                    value={
                        "type": (
                            "work_order_approval"
                        ),
                        "question": (
                            "Approve creating a "
                            "maintenance work order?"
                        ),
                        "incident_id": (
                            "INC-TEST"
                        ),
                        "equipment_id": (
                            "AHU-001"
                        ),
                        "likely_issue": (
                            assessment
                            .likely_issue
                        ),
                        "confidence": (
                            assessment
                            .confidence
                        ),
                        "recommended_next_step": (
                            assessment
                            .recommended_next_step
                        ),
                    }
                )
            ],
        }

    async def fake_resume(
        approved,
        rationale=None,
        workspace_dir=CURRENT_RUN_DIR,
        checkpointer=None,
    ):
        assert workspace_dir == CURRENT_RUN_DIR
        assert checkpointer is (
            app.state.workflow_checkpointer
        )

        assert approved is False

        assert rationale == (
            "Need more evidence."
        )

        approval = ApprovalRecord(
            approved=False,
            rationale=rationale,
        )

        manifest = load_manifest()

        manifest.status = (
            RunStatus.COMPLETE
        )
        manifest.current_step = None

        if (
            PipelineStep.HUMAN_APPROVAL
            not in manifest.completed_steps
        ):
            manifest.completed_steps.append(
                PipelineStep.HUMAN_APPROVAL
            )

        save_manifest(
            manifest
        )

        return {
            "approval": approval,
        }

    monkeypatch.setattr(
        api_main,
        "run_investigation_graph",
        fake_start,
    )

    monkeypatch.setattr(
        api_main,
        "resume_investigation_graph",
        fake_resume,
    )

    start = client.post(
        "/api/workflow/start"
    )

    assert start.status_code == 200

    start_data = start.json()

    assert (
        start_data["status"]
        == "waiting_for_approval"
    )

    assert (
        start_data[
            "approval_request"
        ]["equipment_id"]
        == "AHU-001"
    )

    assert (
        start_data["manifest"][
            "status"
        ]
        == "waiting"
    )

    decision = client.post(
        "/api/workflow/decision",
        json={
            "approved": False,
            "rationale": (
                "Need more evidence."
            ),
        },
    )

    assert decision.status_code == 200

    decision_data = (
        decision.json()
    )

    assert (
        decision_data["status"]
        == "complete"
    )

    assert (
        decision_data[
            "approval"
        ]["approved"]
        is False
    )

    assert (
        decision_data[
            "work_order"
        ]
        is None
    )

    assert (
        decision_data[
            "manifest"
        ]["status"]
        == "complete"
    )


def test_workflow_start_timeout_returns_gateway_timeout(
    client,
    monkeypatch,
):
    async def fake_start(
        workspace_dir,
        checkpointer,
    ):
        assert workspace_dir == CURRENT_RUN_DIR
        raise TimeoutError

    monkeypatch.setattr(
        api_main,
        "run_investigation_graph",
        fake_start,
    )

    response = client.post(
        "/api/workflow/start"
    )

    assert response.status_code == 504
    assert response.json() == {
        "detail": (
            "AI workflow stage timed out."
        )
    }


def test_workflow_artifact_endpoints(
    client,
):
    reset = client.post(
        "/api/runs/reset",
        json=heating_fault_payload(),
    )

    assert reset.status_code == 200

    investigation = (
        OperationalInvestigation(
            summary="Evidence gathered.",
            telemetry_findings=[
                "High valve command."
            ],
            maintenance_findings=[
                "Previous calibration."
            ],
            occupant_impact=[
                "Cold complaints."
            ],
            evidence=[
                "Operational evidence."
            ],
        )
    )

    assessment = (
        InvestigationAssessment(
            likely_issue=(
                "Possible actuator issue."
            ),
            confidence=0.8,
            telemetry_findings=[],
            maintenance_findings=[],
            occupant_impact=[],
            evidence=[],
            recommended_next_step=(
                "Inspect actuator."
            ),
        )
    )

    approval = ApprovalRecord(
        approved=True,
        rationale="Approved.",
    )

    work_order = (
        WorkOrderCreationResult(
            created=True,
            work_order=WorkOrder(
                id="WO-TEST",
                building_id="BLDG-001",
                equipment_id="AHU-001",
                created_at=(
                    "2026-01-15T12:00:00Z"
                ),
                description=(
                    "Inspect actuator."
                ),
                status=(
                    WorkOrderStatus.OPEN
                ),
            ),
        )
    )

    trace = [
        ToolTraceEntry(
            event="tool_call",
            tool_name=(
                "get_equipment_sensors"
            ),
            tool_call_id="call-1",
            arguments={
                "equipment_id": "AHU-001"
            },
        ),
        ToolTraceEntry(
            event="tool_result",
            tool_name=(
                "get_equipment_sensors"
            ),
            tool_call_id="call-1",
            content=(
                '{"result": []}'
            ),
        ),
    ]

    (
        CURRENT_RUN_DIR
        / INVESTIGATION_FILE
    ).write_text(
        investigation.model_dump_json(
            indent=2
        ),
        encoding="utf-8",
    )

    (
        CURRENT_RUN_DIR
        / ASSESSMENT_FILE
    ).write_text(
        assessment.model_dump_json(
            indent=2
        ),
        encoding="utf-8",
    )

    (
        CURRENT_RUN_DIR
        / APPROVAL_FILE
    ).write_text(
        approval.model_dump_json(
            indent=2
        ),
        encoding="utf-8",
    )

    (
        CURRENT_RUN_DIR
        / WORK_ORDER_FILE
    ).write_text(
        work_order.model_dump_json(
            indent=2
        ),
        encoding="utf-8",
    )

    (
        CURRENT_RUN_DIR
        / MCP_TRACE_FILE
    ).write_text(
        "\n".join(
            entry.model_dump_json()
            for entry in trace
        ),
        encoding="utf-8",
    )

    response = client.get(
        "/api/artifacts/investigation"
    )

    assert response.status_code == 200

    assert (
        response.json()["summary"]
        == "Evidence gathered."
    )

    response = client.get(
        "/api/artifacts/mcp-trace"
    )

    assert response.status_code == 200
    assert len(response.json()) == 2

    response = client.get(
        "/api/artifacts/assessment"
    )

    assert response.status_code == 200

    assert (
        response.json()["confidence"]
        == 0.8
    )

    response = client.get(
        "/api/artifacts/approval"
    )

    assert response.status_code == 200

    assert (
        response.json()["approved"]
        is True
    )

    response = client.get(
        "/api/artifacts/work-order"
    )

    assert response.status_code == 200

    assert (
        response.json()[
            "work_order"
        ]["id"]
        == "WO-TEST"
    )
