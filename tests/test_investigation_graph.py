from datetime import datetime
from langgraph.checkpoint.memory import InMemorySaver

import pytest

from propertyops_ai_investigator.domain.models import (
    ApprovalRecord,
    IncidentSeverity,
    InvestigationAssessment,
    OperationalIncident,
    OperationalInvestigation,
    TelemetryEvidence,
)
from propertyops_ai_investigator.rag.retriever import (
    RetrievalResult,
)
from propertyops_ai_investigator.services.investigation_service import (
    InvestigationArtifact,
)
from propertyops_ai_investigator.services.rag_service import (
    RagArtifact,
)
from propertyops_ai_investigator.workflows import (
    investigation_graph,
)

from propertyops_ai_investigator.data.experiment import (
    ExperimentConfig,
    ScenarioType,
)

from propertyops_ai_investigator.services.workspace import (
    APPROVAL_FILE,
    PipelineStep,
    RunManifest,
    RunStatus,
    load_manifest,
    save_manifest,
)


def create_incident() -> OperationalIncident:
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
        evidence=[
            TelemetryEvidence(
                metric="power_kw",
                value=148.3,
                unit="kW",
                aggregation="max",
            )
        ],
    )


@pytest.mark.anyio
async def test_graph_interrupts_for_human_approval_and_resumes_rejection(
    tmp_path,
    monkeypatch,
):
    manifest = RunManifest(
        run_id="test-thread",
        config=ExperimentConfig(
            scenario=ScenarioType.NORMAL_OPERATION,
        ),
    )

    save_manifest(
        manifest,
        tmp_path,
    )

    incident = create_incident()

    (
        tmp_path
        / "incident.json"
    ).write_text(
        incident.model_dump_json(
            indent=2,
        ),
        encoding="utf-8",
    )

    call_order: list[str] = []

    investigation = OperationalInvestigation(
        summary="Operational evidence gathered.",
        telemetry_findings=[
            "High valve command."
        ],
        maintenance_findings=[
            "Previous actuator calibration."
        ],
        occupant_impact=[
            "Cold complaints."
        ],
        evidence=[
            "MCP evidence."
        ],
    )

    rag = RagArtifact(
        query="test query",
        retrieval_queries=[
            "test query"
        ],
        k=1,
        embedding_model="test-model",
        results=[
            RetrievalResult(
                chunk_id="chunk-1",
                source="guide.md",
                text="Inspect actuator.",
                score=0.8,
            )
        ],
    )

    assessment = InvestigationAssessment(
        likely_issue=(
            "Possible heating valve issue."
        ),
        confidence=0.8,
        telemetry_findings=[
            "High valve command."
        ],
        maintenance_findings=[
            "Previous actuator calibration."
        ],
        occupant_impact=[
            "Cold complaints."
        ],
        evidence=[
            "Combined evidence."
        ],
        recommended_next_step=(
            "Inspect actuator and linkage."
        ),
    )

    class FakeInvestigationService:
        def __init__(
            self,
            workspace_dir,
        ):
            assert workspace_dir == tmp_path

        async def run(
            self,
            incident,
        ):
            call_order.append(
                "investigate"
            )

            return InvestigationArtifact(
                investigation=investigation,
                trace=[],
            )

    class FakeRagService:
        def __init__(
            self,
            workspace_dir,
        ):
            assert workspace_dir == tmp_path

        def run(self):
            call_order.append(
                "rag"
            )

            return rag

    class FakeAssessmentService:
        def __init__(
            self,
            workspace_dir,
        ):
            assert workspace_dir == tmp_path

        async def run(
            self,
            incident,
            investigation,
            rag,
        ):
            call_order.append(
                "assessment"
            )

            return assessment

    monkeypatch.setattr(
        investigation_graph,
        "McpInvestigationService",
        FakeInvestigationService,
    )

    monkeypatch.setattr(
        investigation_graph,
        "RagService",
        FakeRagService,
    )

    monkeypatch.setattr(
        investigation_graph,
        "AssessmentService",
        FakeAssessmentService,
    )

    checkpointer = InMemorySaver()

    paused = await (
        investigation_graph
        .run_investigation_graph(
            tmp_path,
            checkpointer=checkpointer,
        )
    )

    assert call_order == [
        "investigate",
        "rag",
        "assessment",
    ]

    assert (
        paused["incident"].id
        == "INC-TEST"
    )

    assert (
        paused["investigation"]
        == investigation
    )

    assert paused["rag"] == rag

    assert (
        paused["assessment"]
        == assessment
    )

    assert "__interrupt__" in paused

    interrupts = paused[
        "__interrupt__"
    ]

    assert len(interrupts) == 1

    payload = interrupts[0].value

    assert (
        payload["type"]
        == "work_order_approval"
    )

    assert (
        payload["incident_id"]
        == "INC-TEST"
    )

    assert (
        payload["equipment_id"]
        == "AHU-001"
    )

    assert (
        payload["likely_issue"]
        == assessment.likely_issue
    )

    assert (
        payload["recommended_next_step"]
        == assessment.recommended_next_step
    )

    waiting_manifest = load_manifest(
        tmp_path
    )

    assert (
        waiting_manifest.status
        == RunStatus.WAITING
    )

    assert (
        waiting_manifest.current_step
        == PipelineStep.HUMAN_APPROVAL
    )

    assert not (
        tmp_path
        / APPROVAL_FILE
    ).exists()

    resumed = await (
        investigation_graph
        .resume_investigation_graph(
            approved=False,
            rationale=(
                "Need more evidence before "
                "dispatching maintenance."
            ),
            workspace_dir=tmp_path,
            checkpointer=checkpointer,
        )
    )

    # Resuming the approval interrupt must not
    # repeat the earlier graph nodes.
    assert call_order == [
        "investigate",
        "rag",
        "assessment",
    ]

    assert (
        resumed["approval"].approved
        is False
    )

    assert (
        resumed["approval"].rationale
        == (
            "Need more evidence before "
            "dispatching maintenance."
        )
    )

    approval_path = (
        tmp_path
        / APPROVAL_FILE
    )

    assert approval_path.exists()

    persisted_approval = (
        ApprovalRecord.model_validate_json(
            approval_path.read_text(
                encoding="utf-8"
            )
        )
    )

    assert (
        persisted_approval.approved
        is False
    )

    final_manifest = load_manifest(
        tmp_path
    )

    assert (
        final_manifest.status
        == RunStatus.READY
    )

    assert (
        final_manifest.current_step
        is None
    )

    assert (
        PipelineStep.HUMAN_APPROVAL
        in final_manifest.completed_steps
    )