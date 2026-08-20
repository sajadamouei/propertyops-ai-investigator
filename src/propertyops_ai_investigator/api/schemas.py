from typing import Any

from pydantic import BaseModel

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


class ResetRunRequest(BaseModel):
    config: ExperimentConfig


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