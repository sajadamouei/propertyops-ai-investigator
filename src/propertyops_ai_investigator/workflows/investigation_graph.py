import json
from pathlib import Path
from typing import Any

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
    incident: dict[str, Any]

    investigation: dict[str, Any]
    mcp_trace: list[dict[str, Any]]

    rag: dict[str, Any]

    assessment: dict[str, Any]

    approval: dict[str, Any]

    work_order: dict[str, Any]


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


def build_approval_request(
    incident: OperationalIncident,
    assessment: InvestigationAssessment,
) -> dict[str, Any]:
    return {
        "type": "work_order_approval",
        "question": (
            "Approve creating a maintenance "
            "work order?"
        ),
        "incident_id": incident.id,
        "equipment_id": incident.equipment_id,
        "likely_issue": assessment.likely_issue,
        "confidence": assessment.confidence,
        "recommended_next_step": (
            assessment.recommended_next_step
        ),
    }

def route_after_approval(
    state: InvestigationGraphState,
) -> str:
    approval_data = state.get(
        "approval"
    )

    if approval_data is None:
        raise RuntimeError(
            "Approval decision is missing."
        )

    approval = ApprovalRecord.model_validate(
        approval_data
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
        incident = OperationalIncident.model_validate(
            state["incident"]
        )

        artifact = await (
            McpInvestigationService(
                workspace_dir
            ).run(
                incident=incident
            )
        )

        return {
            "investigation": (
                artifact.investigation
                .model_dump(mode="json")
            ),
            "mcp_trace": [
                entry.model_dump(mode="json")
                for entry in artifact.trace
            ],
        }

    def rag_node(
        state: InvestigationGraphState,
    ) -> dict:
        artifact = RagService(
            workspace_dir
        ).run()

        return {
            "rag": artifact.model_dump(
                mode="json"
            ),
        }

    async def assessment_node(
        state: InvestigationGraphState,
    ) -> dict:
        incident = OperationalIncident.model_validate(
            state["incident"]
        )
        investigation = (
            OperationalInvestigation.model_validate(
                state["investigation"]
            )
        )
        rag = RagArtifact.model_validate(
            state["rag"]
        )

        assessment = await AssessmentService(
            workspace_dir
        ).run(
            incident=incident,
            investigation=investigation,
            rag=rag,
        )

        return {
            "assessment": assessment.model_dump(
                mode="json"
            ),
        }

    def approval_node(
        state: InvestigationGraphState,
    ) -> dict:
        incident = OperationalIncident.model_validate(
            state["incident"]
        )
        assessment = (
            InvestigationAssessment.model_validate(
                state["assessment"]
            )
        )

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
            build_approval_request(
                incident,
                assessment,
            )
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
            "approval": approval.model_dump(
                mode="json"
            ),
        }

    async def work_order_node(
        state: InvestigationGraphState,
    ) -> dict:
        incident = OperationalIncident.model_validate(
            state["incident"]
        )
        assessment = (
            InvestigationAssessment.model_validate(
                state["assessment"]
            )
        )

        result = await WorkOrderService(
            workspace_dir
        ).run(
            incident=incident,
            assessment=assessment,
        )

        return {
            "work_order": result.model_dump(
                mode="json"
            ),
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
            "incident": incident.model_dump(
                mode="json"
            ),
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
