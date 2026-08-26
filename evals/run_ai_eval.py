"""Run the live Heating Valve Fault evaluation through the real stack.

The Property Operations MCP server must already be listening at the URL
configured by ``agents.mcp_tools``.  This runner stops at the graph's human
approval interrupt and therefore never creates a work order.
"""

import asyncio

from langgraph.checkpoint.memory import InMemorySaver

from evals.quality import AIQualityReport, evaluate_heating_valve_quality
from propertyops_ai_investigator.data.experiment import (
    ScenarioType,
    create_scenario_config,
)
from propertyops_ai_investigator.domain.models import (
    InvestigationAssessment,
    OperationalInvestigation,
)
from propertyops_ai_investigator.services.pipeline import PipelineService
from propertyops_ai_investigator.services.rag_service import RagArtifact
from propertyops_ai_investigator.services.workspace import (
    CURRENT_RUN_DIR,
    reset_current_run,
)
from propertyops_ai_investigator.workflows.investigation_graph import (
    run_investigation_graph,
)


def _print_section(report_section) -> None:
    print(report_section.name)

    for check in report_section.checks:
        status = "PASS" if check.passed else "FAIL"
        print(f"  [{status}] {check.name} - {check.detail}")

    print()


def _print_items(label: str, values: list[str]) -> None:
    print(f"  {label}:")

    if not values:
        print("    (none recorded)")
        return

    for value in values:
        print(f"    - {value}")


def print_report(
    report: AIQualityReport,
    investigation: OperationalInvestigation,
    assessment: InvestigationAssessment,
    rag: RagArtifact,
) -> None:
    print(f"Scenario: {report.scenario}")
    print()

    for section in report.sections:
        _print_section(section)

    overall = "PASS" if report.passed else "FAIL"
    print(f"Overall deterministic result: {overall}")
    print()

    print("Final assessment")
    print(f"  likely_issue: {assessment.likely_issue}")
    print(f"  confidence: {assessment.confidence:.3f}")
    print(
        "  recommended_next_step: "
        f"{assessment.recommended_next_step}"
    )
    print()

    print("Manual review material (not automatically scored)")
    print("  Grounding")
    print(f"    Investigation summary: {investigation.summary}")
    _print_items("Telemetry findings", investigation.telemetry_findings)
    _print_items("Maintenance findings", investigation.maintenance_findings)
    _print_items("Occupant impact", investigation.occupant_impact)
    _print_items("Investigation evidence", investigation.evidence)
    print()

    print("  Diagnostic usefulness")
    print(f"    Likely issue: {assessment.likely_issue}")
    _print_items("Assessment evidence", assessment.evidence)
    _print_items("Assessment telemetry", assessment.telemetry_findings)
    print("    Retrieved guidance:")

    for result in rag.results:
        print(
            f"      - [{result.chunk_id} | {result.source}] "
            f"{result.text}"
        )

    print()
    print("  Uncertainty/calibration")
    print(f"    Confidence: {assessment.confidence:.3f}")
    print(f"    Framing: {assessment.likely_issue}")
    print()
    print("  Operational usefulness")
    print(f"    {assessment.recommended_next_step}")


async def run_live_evaluation() -> bool:
    config = create_scenario_config(
        ScenarioType.HEATING_VALVE_FAULT
    )
    reset_current_run(config, CURRENT_RUN_DIR)

    incident = PipelineService(
        CURRENT_RUN_DIR
    ).run_deterministic_pipeline()

    if incident is None:
        raise RuntimeError(
            "Heating Valve Fault scenario did not produce an incident."
        )

    state = await run_investigation_graph(
        CURRENT_RUN_DIR,
        checkpointer=InMemorySaver(),
    )

    investigation = OperationalInvestigation.model_validate(
        state["investigation"]
    )
    assessment = InvestigationAssessment.model_validate(
        state["assessment"]
    )
    rag = RagArtifact.model_validate(state["rag"])

    report = evaluate_heating_valve_quality(
        investigation=investigation,
        trace=state["mcp_trace"],
        assessment=assessment,
        rag=rag,
    )

    print_report(report, investigation, assessment, rag)
    return report.passed


def main() -> int:
    passed = asyncio.run(run_live_evaluation())
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())

