import asyncio
from datetime import datetime

import pytest

from propertyops_ai_investigator.services import (
    assessment_service,
)
from propertyops_ai_investigator.data.experiment import (
    ExperimentConfig,
    ScenarioType,
)
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
from propertyops_ai_investigator.services.assessment_service import (
    AssessmentService,
    build_assessment_prompt,
)
from propertyops_ai_investigator.services.ai_timeout import (
    AI_STAGE_TIMEOUT_SECONDS,
)
from propertyops_ai_investigator.services.rag_service import (
    RagArtifact,
)
from propertyops_ai_investigator.services.workspace import (
    ASSESSMENT_FILE,
    PipelineStep,
    RunManifest,
    RunStatus,
    load_manifest,
    save_manifest,
)


def create_test_inputs():
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

    return incident, investigation, rag


def create_test_manifest(tmp_path):
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


def test_assessment_prompt_separates_evidence_and_guidance():
    incident, investigation, rag = (
        create_test_inputs()
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


@pytest.mark.anyio
async def test_assessment_success_remains_unchanged(
    tmp_path,
    monkeypatch,
):
    create_test_manifest(tmp_path)
    incident, investigation, rag = (
        create_test_inputs()
    )

    expected = InvestigationAssessment(
        likely_issue=(
            "Possible heating valve issue."
        ),
        confidence=0.8,
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
            "Combined evidence."
        ],
        recommended_next_step=(
            "Inspect actuator and linkage."
        ),
    )

    class FakeStructuredModel:
        async def ainvoke(self, prompt):
            assert "AHU-001" in prompt
            return expected

    class FakeModel:
        def with_structured_output(
            self,
            schema,
            method,
        ):
            assert schema is InvestigationAssessment
            assert method == "json_schema"
            return FakeStructuredModel()

    monkeypatch.setattr(
        assessment_service,
        "ChatGoogleGenerativeAI",
        lambda **kwargs: FakeModel(),
    )

    service = AssessmentService(tmp_path)

    assert (
        service.ai_timeout_seconds
        == AI_STAGE_TIMEOUT_SECONDS
        == 60.0
    )

    result = await service.run(
        incident,
        investigation,
        rag,
    )

    assert result == expected
    assert (
        tmp_path / ASSESSMENT_FILE
    ).exists()

    manifest = load_manifest(tmp_path)
    assert manifest.status == RunStatus.READY
    assert manifest.current_step is None
    assert (
        PipelineStep.ASSESSMENT
        in manifest.completed_steps
    )


@pytest.mark.anyio
async def test_assessment_timeout_marks_failed_and_propagates(
    tmp_path,
    monkeypatch,
):
    create_test_manifest(tmp_path)
    incident, investigation, rag = (
        create_test_inputs()
    )

    class HangingStructuredModel:
        async def ainvoke(self, prompt):
            await asyncio.Event().wait()

    class FakeModel:
        def with_structured_output(
            self,
            schema,
            method,
        ):
            return HangingStructuredModel()

    monkeypatch.setattr(
        assessment_service,
        "ChatGoogleGenerativeAI",
        lambda **kwargs: FakeModel(),
    )

    with pytest.raises(TimeoutError):
        await AssessmentService(
            tmp_path,
            ai_timeout_seconds=0.001,
        ).run(
            incident,
            investigation,
            rag,
        )

    manifest = load_manifest(tmp_path)
    assert manifest.status == RunStatus.FAILED
    assert (
        manifest.current_step
        == PipelineStep.ASSESSMENT
    )
    assert (
        PipelineStep.ASSESSMENT
        not in manifest.completed_steps
    )
    assert not (
        tmp_path / ASSESSMENT_FILE
    ).exists()
