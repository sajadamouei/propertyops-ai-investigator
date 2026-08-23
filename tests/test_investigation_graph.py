import json
from datetime import datetime

import pytest

from propertyops_ai_investigator.domain.models import (
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
async def test_graph_runs_investigation_rag_assessment_in_order(
    tmp_path,
    monkeypatch,
):
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

    result = await (
        investigation_graph
        .run_investigation_graph(
            tmp_path
        )
    )

    assert call_order == [
        "investigate",
        "rag",
        "assessment",
    ]

    assert (
        result["incident"].id
        == "INC-TEST"
    )

    assert (
        result["investigation"]
        == investigation
    )

    assert result["rag"] == rag

    assert (
        result["assessment"]
        == assessment
    )