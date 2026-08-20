import json

import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from propertyops_ai_investigator.api.schemas import (
    ArtifactTableResponse,
    DetectionStageResponse,
    FeatureStageResponse,
    GenerateStageResponse,
    IncidentStageResponse,
    ResetRunRequest,
    RunResponse,
)
from propertyops_ai_investigator.services.pipeline import (
    PipelineService,
)
from propertyops_ai_investigator.services.workspace import (
    ANOMALY_SCORES_FILE,
    CURRENT_RUN_DIR,
    DETECTION_FILE,
    EVENTS_FILE,
    FEATURES_FILE,
    RAW_TELEMETRY_FILE,
    PipelineStep,
    load_manifest,
    reset_current_run,
)

from propertyops_ai_investigator.data.experiment import (
    ExperimentConfig,
    ScenarioType,
    create_scenario_config,
)


app = FastAPI(
    title="PropertyOps AI Investigator API",
    version="0.1.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
    }


@app.get(
    "/api/runs/current",
    response_model=RunResponse,
)
def get_current_run() -> RunResponse:
    try:
        manifest = load_manifest()
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail="No current run exists.",
        ) from exc

    return RunResponse(
        manifest=manifest,
    )


@app.post(
    "/api/runs/reset",
    response_model=RunResponse,
)
def reset_run(
    request: ResetRunRequest,
) -> RunResponse:
    if request.scenario == ScenarioType.CUSTOM_FAULT:
        config = ExperimentConfig(
            scenario=request.scenario,
            days=request.days,
            seed=request.seed,
            faults=request.faults,
        )
    else:
        config = create_scenario_config(
            request.scenario,
            days=request.days,
            seed=request.seed,
        )

    manifest = reset_current_run(
        config
    )

    return RunResponse(
        manifest=manifest,
    )


@app.post(
    "/api/pipeline/generate",
    response_model=GenerateStageResponse,
)
def generate_data() -> GenerateStageResponse:
    try:
        readings = PipelineService().generate_data()
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    return GenerateStageResponse(
        step=PipelineStep.GENERATE_DATA,
        row_count=len(readings),
        sensor_ids=sorted(
            readings["sensor_id"]
            .unique()
            .tolist()
        ),
    )


@app.post(
    "/api/pipeline/features",
    response_model=FeatureStageResponse,
)
def engineer_features() -> FeatureStageResponse:
    try:
        features = (
            PipelineService()
            .engineer_features()
        )
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    return FeatureStageResponse(
        step=PipelineStep.FEATURE_ENGINEERING,
        row_count=len(features),
        columns=features.columns.tolist(),
    )


@app.post(
    "/api/pipeline/detect",
    response_model=DetectionStageResponse,
)
def detect_anomalies() -> DetectionStageResponse:
    try:
        scored, events, threshold = (
            PipelineService()
            .detect_anomalies()
        )
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    return DetectionStageResponse(
        step=PipelineStep.ANOMALY_DETECTION,
        threshold=threshold,
        anomalous_observations=int(
            scored["is_anomaly"].sum()
        ),
        event_count=len(events),
    )


@app.post(
    "/api/pipeline/incident",
    response_model=IncidentStageResponse,
)
def build_incident() -> IncidentStageResponse:
    try:
        incident = (
            PipelineService()
            .build_incident()
        )
    except (
        RuntimeError,
        ValueError,
        pd.errors.EmptyDataError,
    ) as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    return IncidentStageResponse(
        step=PipelineStep.BUILD_INCIDENT,
        incident=incident,
    )


def read_csv_artifact(
    filename: str,
    limit: int,
) -> ArtifactTableResponse:
    path = CURRENT_RUN_DIR / filename

    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail=(
                f"Artifact not found: {filename}"
            ),
        )

    df = pd.read_csv(
        path
    )

    preview = df.head(
        limit
    ).copy()

    preview = preview.where(
        pd.notna(preview),
        None,
    )

    return ArtifactTableResponse(
        columns=df.columns.tolist(),
        rows=preview.to_dict(
            orient="records"
        ),
        total_rows=len(df),
    )


@app.get(
    "/api/artifacts/raw-telemetry",
    response_model=ArtifactTableResponse,
)
def get_raw_telemetry(
    limit: int = Query(
        default=100,
        ge=1,
        le=1000,
    ),
) -> ArtifactTableResponse:
    return read_csv_artifact(
        RAW_TELEMETRY_FILE,
        limit,
    )


@app.get(
    "/api/artifacts/features",
    response_model=ArtifactTableResponse,
)
def get_features(
    limit: int = Query(
        default=100,
        ge=1,
        le=1000,
    ),
) -> ArtifactTableResponse:
    return read_csv_artifact(
        FEATURES_FILE,
        limit,
    )


@app.get(
    "/api/artifacts/anomaly-scores",
    response_model=ArtifactTableResponse,
)
def get_anomaly_scores(
    limit: int = Query(
        default=100,
        ge=1,
        le=1000,
    ),
) -> ArtifactTableResponse:
    return read_csv_artifact(
        ANOMALY_SCORES_FILE,
        limit,
    )


@app.get(
    "/api/artifacts/events",
    response_model=ArtifactTableResponse,
)
def get_events(
    limit: int = Query(
        default=100,
        ge=1,
        le=1000,
    ),
) -> ArtifactTableResponse:
    return read_csv_artifact(
        EVENTS_FILE,
        limit,
    )


@app.get("/api/artifacts/detection")
def get_detection_summary() -> dict:
    path = (
        CURRENT_RUN_DIR
        / DETECTION_FILE
    )

    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail="Detection artifact not found.",
        )

    return json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )