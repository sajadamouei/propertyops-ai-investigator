import json
from contextlib import asynccontextmanager

import pandas as pd
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from propertyops_ai_investigator.api.schemas import (
    ArtifactTableResponse,
    DetectionSummaryResponse,
    DetectionStageResponse,
    FeatureStageResponse,
    GenerateStageResponse,
    IncidentStageResponse,
    RagStageRequest,
    RagStageResponse,
    ResetRunRequest,
    RunRecoveryResponse,
    RunResponse,
    WorkflowApprovalPrompt,
    WorkflowDecisionRequest,
    WorkflowDecisionResponse,
    WorkflowStartResponse,
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
    INCIDENT_FILE,
    RAW_TELEMETRY_FILE,
    RAG_RESULTS_FILE,
    PipelineStep,
    RunStatus,
    load_manifest,
    reset_current_run,
    APPROVAL_FILE,
    ASSESSMENT_FILE,
    CHECKPOINT_DB_PATH,
    INVESTIGATION_FILE,
    MCP_TRACE_FILE,
    WORK_ORDER_FILE,
)

from propertyops_ai_investigator.data.experiment import (
    ExperimentConfig,
    ScenarioType,
    create_scenario_config,
)


from propertyops_ai_investigator.services.rag_service import (
    RagArtifact,
    RagService,
)

from propertyops_ai_investigator.workflows.investigation_graph import (
    build_approval_request,
    resume_investigation_graph,
    run_investigation_graph,
)

from propertyops_ai_investigator.domain.models import (
    ApprovalRecord,
    InvestigationAssessment,
    OperationalIncident,
    OperationalInvestigation,
    WorkOrderCreationResult,
)

from propertyops_ai_investigator.services.investigation_service import (
    ToolTraceEntry,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    CHECKPOINT_DB_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    async with AsyncSqliteSaver.from_conn_string(
        str(CHECKPOINT_DB_PATH)
    ) as checkpointer:
        app.state.workflow_checkpointer = (
            checkpointer
        )
        yield


app = FastAPI(
    title="PropertyOps AI Investigator API",
    version="0.1.0",
    lifespan=lifespan,
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
    
@app.post(
    "/api/pipeline/rag",
    response_model=RagStageResponse,
)
def run_rag(
    request: RagStageRequest,
) -> RagStageResponse:
    try:
        artifact = RagService().run(
            query=request.query,
            k=request.k,
        )

    except (
        RuntimeError,
        ValueError,
    ) as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    return RagStageResponse(
        step=PipelineStep.RAG,
        query=artifact.query,
        retrieval_queries=(
            artifact.retrieval_queries
        ),
        embedding_model=(
            artifact.embedding_model
        ),
        results=artifact.results,
    )
    
@app.get(
    "/api/artifacts/rag",
    response_model=RagArtifact,
)
def get_rag_results() -> RagArtifact:
    path = (
        CURRENT_RUN_DIR
        / RAG_RESULTS_FILE
    )

    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail="RAG artifact not found.",
        )

    return RagArtifact.model_validate_json(
        path.read_text(
            encoding="utf-8"
        )
    )

@app.post(
    "/api/workflow/start",
    response_model=WorkflowStartResponse,
)
async def start_workflow(
    request: Request,
) -> WorkflowStartResponse:
    try:
        result = await (
            run_investigation_graph(
                checkpointer=(
                    request.app.state
                    .workflow_checkpointer
                )
            )
        )

        interrupts = result.get(
            "__interrupt__",
            [],
        )

        if len(interrupts) != 1:
            raise RuntimeError(
                "Workflow did not pause at "
                "the expected approval step."
            )

        approval_request = (
            WorkflowApprovalPrompt
            .model_validate(
                interrupts[0].value
            )
        )

        manifest = load_manifest()

        return WorkflowStartResponse(
            status=(
                "waiting_for_approval"
            ),
            manifest=manifest,
            investigation=result[
                "investigation"
            ],
            mcp_trace=result[
                "mcp_trace"
            ],
            rag=result["rag"],
            assessment=result[
                "assessment"
            ],
            approval_request=(
                approval_request
            ),
        )

    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail="No current run exists.",
        ) from exc

    except (
        RuntimeError,
        ValueError,
        KeyError,
    ) as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

@app.post(
    "/api/workflow/decision",
    response_model=WorkflowDecisionResponse,
)
async def decide_workflow(
    request: WorkflowDecisionRequest,
    http_request: Request,
) -> WorkflowDecisionResponse:
    try:
        manifest = load_manifest()

    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail="No current run exists.",
        ) from exc

    if (
        manifest.status
        != RunStatus.WAITING
        or manifest.current_step
        != PipelineStep.HUMAN_APPROVAL
    ):
        raise HTTPException(
            status_code=409,
            detail=(
                "Workflow is not currently "
                "waiting for human approval."
            ),
        )

    try:
        result = await (
            resume_investigation_graph(
                approved=request.approved,
                rationale=request.rationale,
                checkpointer=(
                    http_request.app.state
                    .workflow_checkpointer
                ),
            )
        )

        final_manifest = load_manifest()

        return WorkflowDecisionResponse(
            status="complete",
            manifest=final_manifest,
            approval=result[
                "approval"
            ],
            work_order=result.get(
                "work_order"
            ),
        )

    except (
        RuntimeError,
        ValueError,
        KeyError,
    ) as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

@app.get(
    "/api/artifacts/investigation",
    response_model=OperationalInvestigation,
)
def get_investigation_artifact(
) -> OperationalInvestigation:
    path = (
        CURRENT_RUN_DIR
        / INVESTIGATION_FILE
    )

    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail=(
                "Investigation artifact "
                "not found."
            ),
        )

    return (
        OperationalInvestigation
        .model_validate_json(
            path.read_text(
                encoding="utf-8"
            )
        )
    )


@app.get(
    "/api/artifacts/mcp-trace",
    response_model=list[ToolTraceEntry],
)
def get_mcp_trace_artifact(
) -> list[ToolTraceEntry]:
    path = (
        CURRENT_RUN_DIR
        / MCP_TRACE_FILE
    )

    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail=(
                "MCP trace artifact "
                "not found."
            ),
        )

    entries: list[
        ToolTraceEntry
    ] = []

    for line in path.read_text(
        encoding="utf-8"
    ).splitlines():
        line = line.strip()

        if not line:
            continue

        entries.append(
            ToolTraceEntry
            .model_validate_json(
                line
            )
        )

    return entries


@app.get(
    "/api/artifacts/assessment",
    response_model=InvestigationAssessment,
)
def get_assessment_artifact(
) -> InvestigationAssessment:
    path = (
        CURRENT_RUN_DIR
        / ASSESSMENT_FILE
    )

    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail=(
                "Assessment artifact "
                "not found."
            ),
        )

    return (
        InvestigationAssessment
        .model_validate_json(
            path.read_text(
                encoding="utf-8"
            )
        )
    )


@app.get(
    "/api/artifacts/approval",
    response_model=ApprovalRecord,
)
def get_approval_artifact(
) -> ApprovalRecord:
    path = (
        CURRENT_RUN_DIR
        / APPROVAL_FILE
    )

    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail=(
                "Approval artifact "
                "not found."
            ),
        )

    return (
        ApprovalRecord
        .model_validate_json(
            path.read_text(
                encoding="utf-8"
            )
        )
    )


@app.get(
    "/api/artifacts/work-order",
    response_model=WorkOrderCreationResult,
)
def get_work_order_artifact(
) -> WorkOrderCreationResult:
    path = (
        CURRENT_RUN_DIR
        / WORK_ORDER_FILE
    )

    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail=(
                "Work-order artifact "
                "not found."
            ),
        )

    return (
        WorkOrderCreationResult
        .model_validate_json(
            path.read_text(
                encoding="utf-8"
            )
        )
    )


@app.get(
    "/api/runs/current/recovery",
    response_model=RunRecoveryResponse,
)
def recover_current_run() -> RunRecoveryResponse:
    try:
        manifest = load_manifest(
            CURRENT_RUN_DIR
        )
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail="No current run exists.",
        ) from exc

    raw_telemetry = (
        read_csv_artifact(
            RAW_TELEMETRY_FILE,
            1000,
        )
        if (
            CURRENT_RUN_DIR
            / RAW_TELEMETRY_FILE
        ).exists()
        else None
    )

    generation = None
    if raw_telemetry is not None:
        sensor_ids = (
            pd.read_csv(
                CURRENT_RUN_DIR
                / RAW_TELEMETRY_FILE,
                usecols=["sensor_id"],
            )["sensor_id"]
            .dropna()
            .astype(str)
            .unique()
            .tolist()
        )
        generation = GenerateStageResponse(
            step=PipelineStep.GENERATE_DATA,
            row_count=raw_telemetry.total_rows,
            sensor_ids=sensor_ids,
        )

    features = (
        read_csv_artifact(
            FEATURES_FILE,
            1000,
        )
        if (
            CURRENT_RUN_DIR
            / FEATURES_FILE
        ).exists()
        else None
    )
    feature_stage = (
        FeatureStageResponse(
            step=(
                PipelineStep.FEATURE_ENGINEERING
            ),
            row_count=features.total_rows,
            columns=features.columns,
        )
        if features is not None
        else None
    )

    detection_summary = None
    detection_stage = None
    detection_path = (
        CURRENT_RUN_DIR
        / DETECTION_FILE
    )
    if detection_path.exists():
        detection_summary = (
            DetectionSummaryResponse
            .model_validate_json(
                detection_path.read_text(
                    encoding="utf-8"
                )
            )
        )
        detection_stage = (
            DetectionStageResponse(
                step=(
                    PipelineStep
                    .ANOMALY_DETECTION
                ),
                **detection_summary.model_dump(),
            )
        )

    anomaly_scores = (
        read_csv_artifact(
            ANOMALY_SCORES_FILE,
            1000,
        )
        if (
            CURRENT_RUN_DIR
            / ANOMALY_SCORES_FILE
        ).exists()
        else None
    )
    events = (
        read_csv_artifact(
            EVENTS_FILE,
            1000,
        )
        if (
            CURRENT_RUN_DIR
            / EVENTS_FILE
        ).exists()
        else None
    )

    incident = None
    incident_stage = None
    incident_path = (
        CURRENT_RUN_DIR
        / INCIDENT_FILE
    )
    if incident_path.exists():
        incident_data = json.loads(
            incident_path.read_text(
                encoding="utf-8"
            )
        )
        if incident_data is not None:
            incident = (
                OperationalIncident
                .model_validate(
                    incident_data
                )
            )
        incident_stage = IncidentStageResponse(
            step=PipelineStep.BUILD_INCIDENT,
            incident=incident,
        )

    investigation_path = (
        CURRENT_RUN_DIR
        / INVESTIGATION_FILE
    )
    investigation = (
        get_investigation_artifact()
        if investigation_path.exists()
        else None
    )

    trace_path = (
        CURRENT_RUN_DIR
        / MCP_TRACE_FILE
    )
    mcp_trace = (
        get_mcp_trace_artifact()
        if trace_path.exists()
        else []
    )

    rag_path = (
        CURRENT_RUN_DIR
        / RAG_RESULTS_FILE
    )
    rag = (
        get_rag_results()
        if rag_path.exists()
        else None
    )

    assessment_path = (
        CURRENT_RUN_DIR
        / ASSESSMENT_FILE
    )
    assessment = (
        get_assessment_artifact()
        if assessment_path.exists()
        else None
    )

    approval_path = (
        CURRENT_RUN_DIR
        / APPROVAL_FILE
    )
    approval = (
        get_approval_artifact()
        if approval_path.exists()
        else None
    )

    work_order_path = (
        CURRENT_RUN_DIR
        / WORK_ORDER_FILE
    )
    work_order = (
        get_work_order_artifact()
        if work_order_path.exists()
        else None
    )

    approval_request = None
    if (
        manifest.status == RunStatus.WAITING
        and manifest.current_step
        == PipelineStep.HUMAN_APPROVAL
        and incident is not None
        and assessment is not None
    ):
        approval_request = (
            WorkflowApprovalPrompt
            .model_validate(
                build_approval_request(
                    incident,
                    assessment,
                )
            )
        )

    return RunRecoveryResponse(
        manifest=manifest,
        generation=generation,
        raw_telemetry=raw_telemetry,
        feature_stage=feature_stage,
        features=features,
        detection_stage=detection_stage,
        anomaly_scores=anomaly_scores,
        events=events,
        detection_summary=(
            detection_summary
        ),
        incident_stage=incident_stage,
        investigation=investigation,
        mcp_trace=mcp_trace,
        rag=rag,
        assessment=assessment,
        approval_request=approval_request,
        approval=approval,
        work_order=work_order,
    )
