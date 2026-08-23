import json
from datetime import timedelta
from pathlib import Path
from typing import Literal

from langchain.agents import create_agent
from langchain.agents.structured_output import (
    ToolStrategy,
)
from langchain_google_genai import (
    ChatGoogleGenerativeAI,
)
from pydantic import BaseModel

from propertyops_ai_investigator.agents.mcp_tools import (
    READ_TOOLS,
)
from propertyops_ai_investigator.domain.models import (
    OperationalIncident,
    OperationalInvestigation,
)
from propertyops_ai_investigator.services.workspace import (
    CURRENT_RUN_DIR,
    INCIDENT_FILE,
    INVESTIGATION_FILE,
    MCP_TRACE_FILE,
    PipelineStep,
    RunStatus,
    load_manifest,
    save_manifest,
)


class ToolTraceEntry(BaseModel):
    event: Literal[
        "tool_call",
        "tool_result",
    ]

    tool_name: str
    tool_call_id: str | None = None

    arguments: dict | None = None
    content: str | None = None


class InvestigationArtifact(BaseModel):
    investigation: OperationalInvestigation
    trace: list[ToolTraceEntry]


def build_investigation_prompt(
    incident: OperationalIncident,
) -> str:
    complaint_start = (
        incident.ended_at
        + timedelta(hours=1)
    )

    complaint_end = (
        incident.ended_at
        + timedelta(hours=7)
    )

    evidence_lines = []

    for evidence in incident.evidence:
        unit = (
            f" {evidence.unit}"
            if evidence.unit
            else ""
        )

        evidence_lines.append(
            (
                f"- {evidence.metric} "
                f"{evidence.aggregation}: "
                f"{evidence.value:.2f}"
                f"{unit}"
            )
        )

    evidence_text = "\n".join(
        evidence_lines
    )

    return f"""
Investigate this operational incident.

Incident:
- id: {incident.id}
- building: {incident.building_id}
- equipment: {incident.equipment_id}
- start: {incident.started_at.isoformat()}
- end: {incident.ended_at.isoformat()}
- severity: {incident.severity.value}

Initial anomaly evidence:
{evidence_text}

Investigation requirements:

1. First discover the valid sensor IDs for
   {incident.equipment_id}.
   Never invent sensor IDs.

2. Retrieve relevant telemetry for the incident
   window using those discovered sensor IDs.

3. Review maintenance history for
   {incident.equipment_id}.

4. Review tenant complaints for
   {incident.building_id}
   between
   {complaint_start.isoformat()}
   and
   {complaint_end.isoformat()}.

5. Report only evidence-backed operational
   findings.

Do not perform write actions.

Do not claim a confirmed root cause unless the
operational evidence proves it.

This step gathers operational evidence only.
Do not make the final cross-source assessment;
that happens in a later workflow step.
""".strip()


def extract_tool_trace(
    messages: list,
) -> list[ToolTraceEntry]:
    trace: list[ToolTraceEntry] = []
    mcp_tool_names = {
        "get_equipment_sensors",
        "get_work_orders",
        "get_tenant_complaints",
        "get_telemetry",
    }

    for message in messages:
        tool_calls = getattr(
            message,
            "tool_calls",
            None,
        )

        if tool_calls:
            for tool_call in tool_calls:
                if (
                    tool_call["name"]
                    not in mcp_tool_names
                ):
                    continue

                trace.append(
                    ToolTraceEntry(
                        event="tool_call",
                        tool_name=(
                            tool_call["name"]
                        ),
                        tool_call_id=(
                            tool_call.get("id")
                        ),
                        arguments=(
                            tool_call["args"]
                        ),
                    )
                )

        if getattr(
            message,
            "type",
            None,
        ) == "tool":
            tool_name = (
                getattr(
                    message,
                    "name",
                    None,
                )
                or "unknown"
            )

            if tool_name not in mcp_tool_names:
                continue

            content = message.content

            if not isinstance(
                content,
                str,
            ):
                content = json.dumps(
                    content,
                    default=str,
                )

            trace.append(
                ToolTraceEntry(
                    event="tool_result",
                    tool_name=tool_name,
                    tool_call_id=(
                        getattr(
                            message,
                            "tool_call_id",
                            None,
                        )
                    ),
                    content=content,
                )
            )
            
    return trace


class McpInvestigationService:
    def __init__(
        self,
        workspace_dir: Path = CURRENT_RUN_DIR,
    ) -> None:
        self.workspace_dir = workspace_dir

    def _load_incident(
        self,
    ) -> OperationalIncident:
        path = (
            self.workspace_dir
            / INCIDENT_FILE
        )

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
                "for investigation."
            )

        return OperationalIncident.model_validate(
            data
        )

    async def run(
        self,
        incident: OperationalIncident
        | None = None,
    ) -> InvestigationArtifact:
        manifest = load_manifest(
            self.workspace_dir
        )

        manifest.status = RunStatus.RUNNING
        manifest.current_step = (
            PipelineStep.AI_INVESTIGATION
        )

        save_manifest(
            manifest,
            self.workspace_dir,
        )

        try:
            if incident is None:
                incident = (
                    self._load_incident()
                )

            model = ChatGoogleGenerativeAI(
                model="gemini-3.5-flash-lite",
                thinking_level="minimal",
            )

            agent = create_agent(
                model=model,
                tools=READ_TOOLS,
                response_format=ToolStrategy(
                    OperationalInvestigation
                ),
                system_prompt=(
                    "You are a property operations "
                    "investigation assistant. "
                    "Use operational tools to gather "
                    "evidence about detected incidents. "

                    "Rules: "
                    "Use tools for factual operational "
                    "information. "
                    "Discover valid sensor IDs before "
                    "requesting telemetry. "
                    "Never invent telemetry, maintenance "
                    "records, complaints, or sensor IDs. "
                    "Distinguish observations from "
                    "hypotheses. "
                    "Do not perform write actions. "
                    "Do not produce the final combined "
                    "technical assessment."
                ),
            )

            result = await agent.ainvoke(
                {
                    "messages": [
                        {
                            "role": "user",
                            "content": (
                                build_investigation_prompt(
                                    incident
                                )
                            ),
                        }
                    ]
                }
            )

            investigation = result[
                "structured_response"
            ]

            trace = extract_tool_trace(
                result["messages"]
            )

            (
                self.workspace_dir
                / INVESTIGATION_FILE
            ).write_text(
                investigation.model_dump_json(
                    indent=2,
                ),
                encoding="utf-8",
            )

            trace_path = (
                self.workspace_dir
                / MCP_TRACE_FILE
            )

            trace_path.write_text(
                "\n".join(
                    entry.model_dump_json()
                    for entry in trace
                ),
                encoding="utf-8",
            )

            if (
                PipelineStep.AI_INVESTIGATION
                not in manifest.completed_steps
            ):
                manifest.completed_steps.append(
                    PipelineStep.AI_INVESTIGATION
                )

            manifest.status = RunStatus.READY
            manifest.current_step = None

            save_manifest(
                manifest,
                self.workspace_dir,
            )

            return InvestigationArtifact(
                investigation=investigation,
                trace=trace,
            )

        except Exception:
            manifest.status = RunStatus.FAILED
            manifest.current_step = (
                PipelineStep.AI_INVESTIGATION
            )

            save_manifest(
                manifest,
                self.workspace_dir,
            )

            raise