from typing import Any, Literal

from pydantic import BaseModel, Field

from propertyops_ai_investigator.data.experiment import (
    FaultSpec,
    ScenarioType,
)
from propertyops_ai_investigator.domain.models import (
    ApprovalRecord,
    InvestigationAssessment,
    OperationalIncident,
    OperationalInvestigation,
    WorkOrderCreationResult,
)
from propertyops_ai_investigator.rag.retriever import (
    RetrievalResult,
)
from propertyops_ai_investigator.services.investigation_service import (
    ToolTraceEntry,
)
from propertyops_ai_investigator.services.rag_service import (
    RagArtifact,
)
from propertyops_ai_investigator.services.workspace import (
    PipelineStep,
    RunManifest,
)


class ResetRunRequest(BaseModel):
    scenario: ScenarioType

    days: int = 14
    seed: int = 42

    faults: list[FaultSpec] = Field(
        default_factory=list
    )


class RunResponse(BaseModel):
    manifest: RunManifest


class GenerateStageResponse(BaseModel):
    step: PipelineStep
    row_count: int
    sensor_ids: list[str]


class FeatureStageResponse(BaseModel):
    step: PipelineStep
    row_count: int
    columns: list[str]


class DetectionStageResponse(BaseModel):
    step: PipelineStep

    threshold: float
    anomalous_observations: int
    event_count: int


class DetectionSummaryResponse(BaseModel):
    threshold: float
    anomalous_observations: int
    event_count: int


class IncidentStageResponse(BaseModel):
    step: PipelineStep
    incident: OperationalIncident | None


class ArtifactTableResponse(BaseModel):
    columns: list[str]
    rows: list[dict[str, Any]]
    total_rows: int


class RagStageRequest(BaseModel):
    query: str | None = None

    k: int = Field(
        default=3,
        ge=1,
        le=10,
    )


class RagStageResponse(BaseModel):
    step: PipelineStep
    query: str
    retrieval_queries: list[str]
    embedding_model: str
    results: list[RetrievalResult]


class WorkflowApprovalPrompt(BaseModel):
    type: str
    question: str

    incident_id: str
    equipment_id: str

    likely_issue: str
    confidence: float

    recommended_next_step: str


class RunRecoveryResponse(BaseModel):
    manifest: RunManifest

    generation: GenerateStageResponse | None = None
    raw_telemetry: ArtifactTableResponse | None = None

    feature_stage: FeatureStageResponse | None = None
    features: ArtifactTableResponse | None = None

    detection_stage: DetectionStageResponse | None = None
    anomaly_scores: ArtifactTableResponse | None = None
    events: ArtifactTableResponse | None = None
    detection_summary: DetectionSummaryResponse | None = None

    incident_stage: IncidentStageResponse | None = None

    investigation: OperationalInvestigation | None = None
    mcp_trace: list[ToolTraceEntry] = Field(
        default_factory=list
    )
    rag: RagArtifact | None = None
    assessment: InvestigationAssessment | None = None
    approval_request: WorkflowApprovalPrompt | None = None
    approval: ApprovalRecord | None = None
    work_order: WorkOrderCreationResult | None = None


class WorkflowStartResponse(BaseModel):
    status: Literal[
        "waiting_for_approval"
    ]

    manifest: RunManifest

    investigation: OperationalInvestigation
    mcp_trace: list[ToolTraceEntry]

    rag: RagArtifact

    assessment: InvestigationAssessment

    approval_request: WorkflowApprovalPrompt


class WorkflowDecisionRequest(BaseModel):
    approved: bool
    rationale: str | None = None


class WorkflowDecisionResponse(BaseModel):
    status: Literal["complete"]

    manifest: RunManifest

    approval: ApprovalRecord

    work_order: (
        WorkOrderCreationResult
        | None
    ) = None
