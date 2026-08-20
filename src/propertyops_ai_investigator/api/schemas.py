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