from datetime import datetime

import pytest

from propertyops_ai_investigator.data.experiment import (
    ExperimentConfig,
    ScenarioType,
)
from propertyops_ai_investigator.domain.models import (
    ApprovalRecord,
    IncidentSeverity,
    InvestigationAssessment,
    OperationalIncident,
)
from propertyops_ai_investigator.services import (
    work_order_service,
)
from propertyops_ai_investigator.services.work_order_service import (
    WorkOrderService,
)
from propertyops_ai_investigator.services.workspace import (
    APPROVAL_FILE,
    WORK_ORDER_FILE,
    PipelineStep,
    RunManifest,
    RunStatus,
    load_manifest,
    save_manifest,
)


def create_incident():
    return OperationalIncident(
        id="INC-TEST",
        building_id="BLDG-001",
        equipment_id="AHU-001",
        started_at=datetime(
            2026,
            1,
            15,
            1,
        ),
        ended_at=datetime(
            2026,
            1,
            15,
            5,
        ),
        severity=IncidentSeverity.HIGH,
        anomaly_score=0.7,
        summary="Test incident.",
        evidence=[],
    )


def create_assessment():
    return InvestigationAssessment(
        likely_issue=(
            "Possible heating valve issue."
        ),
        confidence=0.8,
        telemetry_findings=[],
        maintenance_findings=[],
        occupant_impact=[],
        evidence=[],
        recommended_next_step=(
            "Inspect actuator and linkage."
        ),
    )


def create_manifest(
    tmp_path,
):
    save_manifest(
        RunManifest(
            run_id="test-run",
            config=ExperimentConfig(
                scenario=(
                    ScenarioType.NORMAL_OPERATION
                ),
            ),
        ),
        tmp_path,
    )


@pytest.mark.anyio
async def test_work_order_requires_human_approval(
    tmp_path,
    monkeypatch,
):
    create_manifest(
        tmp_path
    )

    ApprovalRecord(
        approved=False,
        rationale="Need more evidence.",
    )

    (
        tmp_path
        / APPROVAL_FILE
    ).write_text(
        ApprovalRecord(
            approved=False,
            rationale="Need more evidence.",
        ).model_dump_json(
            indent=2,
        ),
        encoding="utf-8",
    )

    mcp_called = False

    async def fake_call_mcp_tool(
        tool_name,
        arguments,
    ):
        nonlocal mcp_called
        mcp_called = True

        return {}

    monkeypatch.setattr(
        work_order_service,
        "call_mcp_tool",
        fake_call_mcp_tool,
    )

    with pytest.raises(
        PermissionError
    ):
        await WorkOrderService(
            tmp_path
        ).run(
            create_incident(),
            create_assessment(),
        )

    assert mcp_called is False

    assert not (
        tmp_path
        / WORK_ORDER_FILE
    ).exists()


@pytest.mark.anyio
async def test_approved_work_order_calls_mcp_and_persists(
    tmp_path,
    monkeypatch,
):
    create_manifest(
        tmp_path
    )

    (
        tmp_path
        / APPROVAL_FILE
    ).write_text(
        ApprovalRecord(
            approved=True,
            rationale=(
                "Dispatch technician."
            ),
        ).model_dump_json(
            indent=2,
        ),
        encoding="utf-8",
    )

    captured = {}

    async def fake_call_mcp_tool(
        tool_name,
        arguments,
    ):
        captured["tool_name"] = tool_name
        captured["arguments"] = arguments

        return {
            "result": {
                "created": True,
                "work_order": {
                    "id": "WO-TEST",
                    "building_id": (
                        "BLDG-001"
                    ),
                    "equipment_id": (
                        "AHU-001"
                    ),
                    "created_at": (
                        "2026-01-15T12:00:00Z"
                    ),
                    "description": (
                        arguments[
                            "description"
                        ]
                    ),
                    "status": "open",
                },
            }
        }

    monkeypatch.setattr(
        work_order_service,
        "call_mcp_tool",
        fake_call_mcp_tool,
    )

    result = await WorkOrderService(
        tmp_path
    ).run(
        create_incident(),
        create_assessment(),
    )

    assert result.created is True

    assert (
        result.work_order.id
        == "WO-TEST"
    )

    assert (
        captured["tool_name"]
        == "create_work_order"
    )

    assert (
        captured["arguments"][
            "building_id"
        ]
        == "BLDG-001"
    )

    assert (
        captured["arguments"][
            "equipment_id"
        ]
        == "AHU-001"
    )

    assert (
        "Inspect actuator and linkage"
        in captured[
            "arguments"
        ]["description"]
    )

    assert (
        tmp_path
        / WORK_ORDER_FILE
    ).exists()

    manifest = load_manifest(
        tmp_path
    )

    assert (
        PipelineStep.WORK_ORDER
        in manifest.completed_steps
    )

    assert (
        manifest.status
        == RunStatus.COMPLETE
    )

    assert manifest.current_step is None