import shutil
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from uuid import uuid4

from pydantic import BaseModel, Field

from propertyops_ai_investigator.data.experiment import (
    ExperimentConfig,
)


CURRENT_RUN_DIR = Path(
    "data/runtime/current_run"
)

RAW_TELEMETRY_FILE = "raw_telemetry.csv"
FEATURES_FILE = "features.csv"
ANOMALY_SCORES_FILE = "anomaly_scores.csv"
EVENTS_FILE = "events.csv"
DETECTION_FILE = "detection.json"
INCIDENT_FILE = "incident.json"
RAG_RESULTS_FILE = "rag_results.json"
INVESTIGATION_FILE = "investigation.json"
MCP_TRACE_FILE = "mcp_trace.jsonl"
ASSESSMENT_FILE = "assessment.json"


class PipelineStep(str, Enum):
    GENERATE_DATA = "generate_data"
    FEATURE_ENGINEERING = "feature_engineering"
    ANOMALY_DETECTION = "anomaly_detection"
    BUILD_INCIDENT = "build_incident"
    AI_INVESTIGATION = "ai_investigation"
    RAG = "rag"
    ASSESSMENT = "assessment"
    HUMAN_APPROVAL = "human_approval"
    WORK_ORDER = "work_order"


class RunStatus(str, Enum):
    READY = "ready"
    RUNNING = "running"
    WAITING = "waiting"
    COMPLETE = "complete"
    FAILED = "failed"


class RunManifest(BaseModel):
    run_id: str

    config: ExperimentConfig

    status: RunStatus = RunStatus.READY

    current_step: PipelineStep | None = None

    completed_steps: list[PipelineStep] = Field(
        default_factory=list
    )

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc
        )
    )

    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc
        )
    )


def save_manifest(
    manifest: RunManifest,
    workspace_dir: Path = CURRENT_RUN_DIR,
) -> Path:
    workspace_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    path = workspace_dir / "manifest.json"

    manifest.updated_at = datetime.now(
        timezone.utc
    )

    path.write_text(
        manifest.model_dump_json(
            indent=2,
        ),
        encoding="utf-8",
    )

    return path


def load_manifest(
    workspace_dir: Path = CURRENT_RUN_DIR,
) -> RunManifest:
    path = workspace_dir / "manifest.json"

    return RunManifest.model_validate_json(
        path.read_text(
            encoding="utf-8"
        )
    )


def reset_current_run(
    config: ExperimentConfig,
    workspace_dir: Path = CURRENT_RUN_DIR,
) -> RunManifest:
    if workspace_dir.exists():
        shutil.rmtree(
            workspace_dir
        )

    workspace_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    manifest = RunManifest(
        run_id=uuid4().hex[:12],
        config=config,
    )

    save_manifest(
        manifest,
        workspace_dir,
    )

    return manifest