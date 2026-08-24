from datetime import datetime

from propertyops_ai_investigator.domain.models import (
    IncidentSeverity,
    OperationalIncident,
    OperationalInvestigation,
    TelemetryEvidence,
)
from propertyops_ai_investigator.rag.retriever import (
    RetrievalResult,
)
from propertyops_ai_investigator.services.assessment_service import (
    build_assessment_prompt,
)
from propertyops_ai_investigator.services.rag_service import (
    RagArtifact,
)


def test_assessment_prompt_separates_evidence_and_guidance():
    incident = OperationalIncident(
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
        summary="Heating anomaly.",
        evidence=[
            TelemetryEvidence(
                metric="power_kw",
                value=148.3,
                unit="kW",
                aggregation="max",
            )
        ],
    )

    investigation = OperationalInvestigation(
        summary="Operational evidence gathered.",
        telemetry_findings=[
            "Heating valve was highly open."
        ],
        maintenance_findings=[
            "Previous actuator calibration."
        ],
        occupant_impact=[
            "Cold comfort complaints."
        ],
        evidence=[
            "Telemetry and records retrieved."
        ],
    )

    rag = RagArtifact(
        query="heating troubleshooting",
        retrieval_queries=[
            "heating troubleshooting"
        ],
        k=1,
        embedding_model="test-model",
        results=[
            RetrievalResult(
                chunk_id="guide-1",
                source="guide.md",
                score=0.8,
                text=(
                    "Inspect actuator and linkage "
                    "before replacing components."
                ),
            )
        ],
    )

    prompt = build_assessment_prompt(
        incident,
        investigation,
        rag,
    )

    assert "AHU-001" in prompt

    assert (
        "Previous actuator calibration"
        in prompt
    )

    assert (
        "Inspect actuator and linkage"
        in prompt
    )

    normalized_prompt = " ".join(
        prompt.split()
    )

    assert (
        "diagnostic guidance"
        in normalized_prompt
    )

    assert (
        "not proof"
        in normalized_prompt
    )

    assert (
        "recommended_next_step field must describe only"
        in normalized_prompt
    )

    assert (
        "Do not mention approval, authorization,"
        in normalized_prompt
    )

    assert (
        "work-order creation"
        in normalized_prompt
    )

    assert (
        "assessment only"
        in normalized_prompt
    )