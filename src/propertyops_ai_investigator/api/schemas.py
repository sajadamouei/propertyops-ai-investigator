from typing import Any

from pydantic import BaseModel, Field

from propertyops_ai_investigator.data.experiment import (
    ExperimentConfig,
)
from propertyops_ai_investigator.domain.models import (
    OperationalIncident,
)
from propertyops_ai_investigator.services.workspace import (
    PipelineStep,
    RunManifest,
)

from propertyops_ai_investigator.data.experiment import (
    FaultSpec,
    ScenarioType,
)

from pydantic import BaseModel, Field

from propertyops_ai_investigator.rag.retriever import (
    RetrievalResult,
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