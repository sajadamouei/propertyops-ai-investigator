import json
from pathlib import Path

from langgraph.graph import (
    END,
    START,
    StateGraph,
)
from typing_extensions import TypedDict

from propertyops_ai_investigator.domain.models import (
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
    CURRENT_RUN_DIR,
    INCIDENT_FILE,
)


class InvestigationGraphState(
    TypedDict,
    total=False,
):
    incident: OperationalIncident

    investigation: OperationalInvestigation
    mcp_trace: list[ToolTraceEntry]

    rag: RagArtifact

    assessment: InvestigationAssessment


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


def build_investigation_graph(
    workspace_dir: Path = CURRENT_RUN_DIR,
):
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
        # RagService intentionally reads the same
        # persisted incident artifact used by the
        # rest of the application.
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
        END,
    )

    return builder.compile()


async def run_investigation_graph(
    workspace_dir: Path = CURRENT_RUN_DIR,
) -> InvestigationGraphState:
    incident = load_incident(
        workspace_dir
    )

    graph = build_investigation_graph(
        workspace_dir
    )

    result = await graph.ainvoke(
        {
            "incident": incident,
        }
    )

    return result