import asyncio
import json
from pathlib import Path

from langchain_google_genai import (
    ChatGoogleGenerativeAI,
)

from propertyops_ai_investigator.domain.models import (
    InvestigationAssessment,
    OperationalIncident,
    OperationalInvestigation,
)
from propertyops_ai_investigator.services.rag_service import (
    RagArtifact,
)
from propertyops_ai_investigator.services.ai_timeout import (
    AI_STAGE_TIMEOUT_SECONDS,
)
from propertyops_ai_investigator.services.workspace import (
    ASSESSMENT_FILE,
    CURRENT_RUN_DIR,
    PipelineStep,
    RunStatus,
    load_manifest,
    save_manifest,
)


def build_assessment_prompt(
    incident: OperationalIncident,
    investigation: OperationalInvestigation,
    rag: RagArtifact,
) -> str:
    rag_context = [
        {
            "source": result.source,
            "chunk_id": result.chunk_id,
            "score": result.score,
            "text": result.text,
        }
        for result in rag.results
    ]

    return f"""
Produce the final evidence-based assessment for this
property operations incident.

INCIDENT:
{incident.model_dump_json(indent=2)}

OPERATIONAL INVESTIGATION:
{investigation.model_dump_json(indent=2)}

TECHNICAL GUIDANCE RETRIEVED BY RAG:
{json.dumps(rag_context, indent=2)}

Reason across all three sources.

Important rules:

1. Operational telemetry, maintenance records, and
   tenant complaints are factual evidence gathered from
   operational systems.

2. Retrieved technical documents are diagnostic
   guidance. They are not proof that a particular
   failure occurred.

3. Distinguish observed evidence from hypotheses.

4. Do not claim a confirmed root cause unless the
   evidence actually proves it.

5. Calibrate confidence between 0 and 1.

6. Recommend a concrete next operational action for
   the operator or technician.

7. The recommended_next_step field must describe only
   the operational action itself. Do not mention
   approval, authorization, work-order creation, or
   whether a work order should or should not be
   created.

8. This task is assessment only. Do not claim that
   any recommended action has already been performed.
""".strip()


class AssessmentService:
    def __init__(
        self,
        workspace_dir: Path = CURRENT_RUN_DIR,
        ai_timeout_seconds: float = (
            AI_STAGE_TIMEOUT_SECONDS
        ),
    ) -> None:
        self.workspace_dir = workspace_dir
        self.ai_timeout_seconds = (
            ai_timeout_seconds
        )

    async def run(
        self,
        incident: OperationalIncident,
        investigation: OperationalInvestigation,
        rag: RagArtifact,
    ) -> InvestigationAssessment:
        manifest = load_manifest(
            self.workspace_dir
        )

        manifest.status = RunStatus.RUNNING
        manifest.current_step = (
            PipelineStep.ASSESSMENT
        )

        save_manifest(
            manifest,
            self.workspace_dir,
        )

        try:
            model = ChatGoogleGenerativeAI(
                model="gemini-3.5-flash-lite",
                thinking_level="minimal",
            )

            structured_model = (
                model.with_structured_output(
                    InvestigationAssessment,
                    method="json_schema",
                )
            )

            async with asyncio.timeout(
                self.ai_timeout_seconds
            ):
                assessment = (
                    await structured_model.ainvoke(
                        build_assessment_prompt(
                            incident,
                            investigation,
                            rag,
                        )
                    )
                )

            (
                self.workspace_dir
                / ASSESSMENT_FILE
            ).write_text(
                assessment.model_dump_json(
                    indent=2,
                ),
                encoding="utf-8",
            )

            if (
                PipelineStep.ASSESSMENT
                not in manifest.completed_steps
            ):
                manifest.completed_steps.append(
                    PipelineStep.ASSESSMENT
                )

            manifest.status = RunStatus.READY
            manifest.current_step = None

            save_manifest(
                manifest,
                self.workspace_dir,
            )

            return assessment

        except Exception:
            manifest.status = RunStatus.FAILED
            manifest.current_step = (
                PipelineStep.ASSESSMENT
            )

            save_manifest(
                manifest,
                self.workspace_dir,
            )

            raise
