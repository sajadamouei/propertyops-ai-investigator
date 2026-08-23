from pathlib import Path

from propertyops_ai_investigator.agents.mcp_tools import (
    call_mcp_tool,
)
from propertyops_ai_investigator.domain.models import (
    ApprovalRecord,
    InvestigationAssessment,
    OperationalIncident,
    WorkOrderCreationResult,
)
from propertyops_ai_investigator.services.workspace import (
    APPROVAL_FILE,
    CURRENT_RUN_DIR,
    WORK_ORDER_FILE,
    PipelineStep,
    RunStatus,
    load_manifest,
    save_manifest,
)


def build_work_order_description(
    incident: OperationalIncident,
    assessment: InvestigationAssessment,
) -> str:
    return (
        f"Follow up operational incident "
        f"{incident.id} for "
        f"{incident.equipment_id}. "
        f"Likely issue: "
        f"{assessment.likely_issue}. "
        f"Recommended action: "
        f"{assessment.recommended_next_step}"
    )


class WorkOrderService:
    def __init__(
        self,
        workspace_dir: Path = CURRENT_RUN_DIR,
    ) -> None:
        self.workspace_dir = workspace_dir

    def _require_approval(
        self,
    ) -> ApprovalRecord:
        path = (
            self.workspace_dir
            / APPROVAL_FILE
        )

        if not path.exists():
            raise PermissionError(
                "Work order creation requires "
                "explicit human approval."
            )

        approval = (
            ApprovalRecord.model_validate_json(
                path.read_text(
                    encoding="utf-8"
                )
            )
        )

        if not approval.approved:
            raise PermissionError(
                "Human approval was rejected. "
                "Work order creation is forbidden."
            )

        return approval

    async def run(
        self,
        incident: OperationalIncident,
        assessment: InvestigationAssessment,
    ) -> WorkOrderCreationResult:
        # Defense-in-depth:
        # never rely only on graph routing.
        self._require_approval()

        manifest = load_manifest(
            self.workspace_dir
        )

        manifest.status = RunStatus.RUNNING
        manifest.current_step = (
            PipelineStep.WORK_ORDER
        )

        save_manifest(
            manifest,
            self.workspace_dir,
        )

        try:
            description = (
                build_work_order_description(
                    incident,
                    assessment,
                )
            )

            payload = await call_mcp_tool(
                "create_work_order",
                {
                    "building_id": (
                        incident.building_id
                    ),
                    "equipment_id": (
                        incident.equipment_id
                    ),
                    "description": description,
                },
            )

            if not payload:
                raise RuntimeError(
                    "MCP create_work_order "
                    "returned no structured content."
                )

            result = (
                WorkOrderCreationResult
                .model_validate(
                    payload
                )
            )

            (
                self.workspace_dir
                / WORK_ORDER_FILE
            ).write_text(
                result.model_dump_json(
                    indent=2,
                ),
                encoding="utf-8",
            )

            if (
                PipelineStep.WORK_ORDER
                not in manifest.completed_steps
            ):
                manifest.completed_steps.append(
                    PipelineStep.WORK_ORDER
                )

            manifest.status = (
                RunStatus.COMPLETE
            )
            manifest.current_step = None

            save_manifest(
                manifest,
                self.workspace_dir,
            )

            return result

        except Exception:
            manifest.status = RunStatus.FAILED
            manifest.current_step = (
                PipelineStep.WORK_ORDER
            )

            save_manifest(
                manifest,
                self.workspace_dir,
            )

            raise