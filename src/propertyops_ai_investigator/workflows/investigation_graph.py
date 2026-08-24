import json
from pathlib import Path

from langgraph.checkpoint.memory import (
    InMemorySaver,
)
from langgraph.graph import (
    END,
    START,
    StateGraph,
)
from langgraph.types import (
    Command,
    interrupt,
)
from pydantic import BaseModel
from typing_extensions import TypedDict

from propertyops_ai_investigator.domain.models import (
    ApprovalRecord,
    InvestigationAssessment,
    OperationalIncident,
    OperationalInvestigation,
)
from propertyops_ai_investigator.services.assessment_service import (
    AssessmentService,
)
from propertyops_ai_investigator.services.investigation_service import (
    McpInvestigationService,
    ToolTraceEntry,
)
from propertyops_ai_investigator.services.rag_service import (
    RagArtifact,
    RagService,
)
from propertyops_ai_investigator.services.workspace import (
    APPROVAL_FILE,
    CURRENT_RUN_DIR,
    INCIDENT_FILE,
    PipelineStep,
    RunStatus,
    load_manifest,
    save_manifest,
)

from propertyops_ai_investigator.domain.models import (
    ApprovalRecord,
    InvestigationAssessment,
    OperationalIncident,
    OperationalInvestigation,
    WorkOrderCreationResult,
)

from propertyops_ai_investigator.services.work_order_service import (
    WorkOrderService,
)

DEFAULT_CHECKPOINTER = InMemorySaver()


class HumanApprovalResponse(BaseModel):
    approved: bool
    rationale: str | None = None


class InvestigationGraphState(
    TypedDict,
    total=False,
):
    incident: OperationalIncident

    investigation: OperationalInvestigation
    mcp_trace: list[ToolTraceEntry]

    rag: RagArtifact

    assessment: InvestigationAssessment

    approval: ApprovalRecord

    work_order: WorkOrderCreationResult


def load_incident(
    workspace_dir: Path,
) -> OperationalIncident:
    path = workspace_dir / INCIDENT_FILE

    if not path.exists():
        raise RuntimeError(
            "Incident artifact does not exist."
        )

    data = json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )

    if data is None:
        raise RuntimeError(
            "No operational incident exists "
            "for the investigation graph."
        )

    return OperationalIncident.model_validate(
        data
    )

def route_after_approval(
    state: InvestigationGraphState,
) -> str:
    approval = state.get(
        "approval"
    )

    if approval is None:
        raise RuntimeError(
            "Approval decision is missing."
        )

    if approval.approved:
        return "work_order"

    return "rejected"

def build_investigation_graph(
    workspace_dir: Path = CURRENT_RUN_DIR,
    checkpointer=None,
):
    if checkpointer is None:
        checkpointer = DEFAULT_CHECKPOINTER

    async def investigate_node(
        state: InvestigationGraphState,
    ) -> dict:
        artifact = await (
            McpInvestigationService(
                workspace_dir
            ).run(
                incident=state["incident"]
            )
        )

        return {
            "investigation": (
                artifact.investigation
            ),
            "mcp_trace": artifact.trace,
        }

    def rag_node(
        state: InvestigationGraphState,
    ) -> dict:
        artifact = RagService(
            workspace_dir
        ).run()

        return {
            "rag": artifact,
        }

    async def assessment_node(
        state: InvestigationGraphState,
    ) -> dict:
        assessment = await AssessmentService(
            workspace_dir
        ).run(
            incident=state["incident"],
            investigation=state[
                "investigation"
            ],
            rag=state["rag"],
        )

        return {
            "assessment": assessment,
        }

    def approval_node(
        state: InvestigationGraphState,
    ) -> dict:
        manifest = load_manifest(
            workspace_dir
        )

        manifest.status = RunStatus.WAITING
        manifest.current_step = (
            PipelineStep.HUMAN_APPROVAL
        )

        save_manifest(
            manifest,
            workspace_dir,
        )

        response = interrupt(
            {
                "type": "work_order_approval",
                "question": (
                    "Approve creating a maintenance "
                    "work order?"
                ),
                "incident_id": (
                    state["incident"].id
                ),
                "equipment_id": (
                    state["incident"].equipment_id
                ),
                "likely_issue": (
                    state[
                        "assessment"
                    ].likely_issue
                ),
                "confidence": (
                    state[
                        "assessment"
                    ].confidence
                ),
                "recommended_next_step": (
                    state[
                        "assessment"
                    ].recommended_next_step
                ),
            }
        )

        human_response = (
            HumanApprovalResponse
            .model_validate(
                response
            )
        )

        approval = ApprovalRecord(
            approved=(
                human_response.approved
            ),
            rationale=(
                human_response.rationale
            ),
        )

        (
            workspace_dir
            / APPROVAL_FILE
        ).write_text(
            approval.model_dump_json(
                indent=2,
            ),
            encoding="utf-8",
        )

        manifest = load_manifest(
            workspace_dir
        )

        if (
            PipelineStep.HUMAN_APPROVAL
            not in manifest.completed_steps
        ):
            manifest.completed_steps.append(
                PipelineStep.HUMAN_APPROVAL
            )

        manifest.status = RunStatus.READY
        manifest.current_step = None

        save_manifest(
            manifest,
            workspace_dir,
        )

        return {
            "approval": approval,
        }

    async def work_order_node(
        state: InvestigationGraphState,
    ) -> dict:
        result = await WorkOrderService(
            workspace_dir
        ).run(
            incident=state["incident"],
            assessment=state[
                "assessment"
            ],
        )

        return {
            "work_order": result,
        }

    def rejected_node(
        state: InvestigationGraphState,
    ) -> dict:
        manifest = load_manifest(
            workspace_dir
        )

        manifest.status = (
            RunStatus.COMPLETE
        )
        manifest.current_step = None

        save_manifest(
            manifest,
            workspace_dir,
        )

        return {}

    builder = StateGraph(
        InvestigationGraphState
    )

    builder.add_node(
        "investigate",
        investigate_node,
    )

    builder.add_node(
        "rag",
        rag_node,
    )

    builder.add_node(
        "assessment",
        assessment_node,
    )

    builder.add_node(
        "approval",
        approval_node,
    )

    builder.add_node(
        "work_order",
        work_order_node,
    )

    builder.add_node(
        "rejected",
        rejected_node,
    )

    builder.add_edge(
        START,
        "investigate",
    )

    builder.add_edge(
        "investigate",
        "rag",
    )

    builder.add_edge(
        "rag",
        "assessment",
    )

    builder.add_edge(
        "assessment",
        "approval",
    )

    builder.add_conditional_edges(
        "approval",
        route_after_approval,
        {
            "work_order": "work_order",
            "rejected": "rejected",
        },
    )

    builder.add_edge(
        "work_order",
        END,
    )

    builder.add_edge(
        "rejected",
        END,
    )


    return builder.compile(
        checkpointer=checkpointer
    )


def graph_config(
    workspace_dir: Path,
) -> dict:
    manifest = load_manifest(
        workspace_dir
    )

    return {
        "configurable": {
            "thread_id": manifest.run_id,
        }
    }


async def run_investigation_graph(
    workspace_dir: Path = CURRENT_RUN_DIR,
    checkpointer=None,
) -> InvestigationGraphState:
    incident = load_incident(
        workspace_dir
    )

    graph = build_investigation_graph(
        workspace_dir,
        checkpointer=checkpointer,
    )

    result = await graph.ainvoke(
        {
            "incident": incident,
        },
        config=graph_config(
            workspace_dir
        ),
    )

    return result


async def resume_investigation_graph(
    approved: bool,
    rationale: str | None = None,
    workspace_dir: Path = CURRENT_RUN_DIR,
    checkpointer=None,
) -> InvestigationGraphState:
    graph = build_investigation_graph(
        workspace_dir,
        checkpointer=checkpointer,
    )

    result = await graph.ainvoke(
        Command(
            resume={
                "approved": approved,
                "rationale": rationale,
            }
        ),
        config=graph_config(
            workspace_dir
        ),
    )

    return result