import json

from pydantic import ValidationError
import pytest

from evals.quality import (
    check_assessment_contract,
    check_grounding,
    check_investigation_completeness,
    check_rag,
    evaluate_heating_valve_quality,
)
from propertyops_ai_investigator.domain.models import (
    InvestigationAssessment,
    OperationalInvestigation,
)
from propertyops_ai_investigator.rag.retriever import RetrievalResult
from propertyops_ai_investigator.services.investigation_service import (
    ToolTraceEntry,
)
from propertyops_ai_investigator.services.rag_service import RagArtifact


def create_investigation() -> OperationalInvestigation:
    return OperationalInvestigation(
        summary="AHU-001 did not deliver the requested heat.",
        telemetry_findings=[
            "The valve command was high while supply air stayed cold."
        ],
        # These may legitimately be empty for an incident.
        maintenance_findings=[],
        occupant_impact=[],
        evidence=[
            "Telemetry was retrieved for discovered AHU-001 sensors."
        ],
    )


def create_assessment(
    *,
    likely_issue: str = "Possible heating valve actuator fault.",
    recommended_next_step: str = (
        "Inspect the actuator linkage and confirm actual valve movement."
    ),
) -> InvestigationAssessment:
    return InvestigationAssessment(
        likely_issue=likely_issue,
        confidence=0.78,
        telemetry_findings=[
            "High valve demand coincided with low supply temperature."
        ],
        maintenance_findings=[],
        occupant_impact=[],
        evidence=[
            "Telemetry and prior maintenance records support inspection."
        ],
        recommended_next_step=recommended_next_step,
    )


def create_rag() -> RagArtifact:
    return RagArtifact(
        query="heating valve troubleshooting",
        retrieval_queries=["heating valve troubleshooting"],
        k=1,
        embedding_model="test-model",
        results=[
            RetrievalResult(
                chunk_id="heating-guide-1",
                source="heating-guide.md",
                text="Inspect the actuator and mechanical linkage.",
                score=0.91,
            )
        ],
    )


def create_grounded_trace() -> list[ToolTraceEntry]:
    return [
        ToolTraceEntry(
            event="tool_call",
            tool_name="get_equipment_sensors",
            tool_call_id="sensors-1",
            arguments={"equipment_id": "AHU-001"},
        ),
        ToolTraceEntry(
            event="tool_result",
            tool_name="get_equipment_sensors",
            tool_call_id="sensors-1",
            content=json.dumps(
                {
                    "result": [
                        {"id": "AHU01-HEAT-VALVE"},
                        {"id": "AHU01-SUPPLY-TEMP"},
                    ]
                }
            ),
        ),
        ToolTraceEntry(
            event="tool_call",
            tool_name="get_telemetry",
            tool_call_id="telemetry-1",
            arguments={
                "sensor_ids": [
                    "AHU01-HEAT-VALVE",
                    "AHU01-SUPPLY-TEMP",
                ],
                "start": "2026-01-15T01:00:00",
                "end": "2026-01-15T05:00:00",
            },
        ),
        ToolTraceEntry(
            event="tool_call",
            tool_name="get_work_orders",
            tool_call_id="work-orders-1",
            arguments={"equipment_id": "AHU-001"},
        ),
        ToolTraceEntry(
            event="tool_call",
            tool_name="get_tenant_complaints",
            tool_call_id="complaints-1",
            arguments={
                "building_id": "BLDG-001",
                "start": "2026-01-15T06:00:00",
                "end": "2026-01-15T12:00:00",
            },
        ),
    ]


def checks_by_name(section):
    return {
        check.name: check
        for check in section.checks
    }


def test_known_heating_valve_artifacts_pass_all_checks():
    report = evaluate_heating_valve_quality(
        investigation=create_investigation(),
        trace=create_grounded_trace(),
        assessment=create_assessment(),
        rag=create_rag(),
    )

    assert report.passed is True
    assert all(section.passed for section in report.sections)


def test_grounding_requires_every_read_tool_and_rejects_write_tool():
    trace = create_grounded_trace()
    trace = [
        entry
        for entry in trace
        if entry.tool_name != "get_tenant_complaints"
    ]
    trace.append(
        ToolTraceEntry(
            event="tool_call",
            tool_name="create_work_order",
            arguments={"description": "Replace actuator."},
        )
    )

    checks = checks_by_name(check_grounding(trace))

    assert checks[
        "required MCP call: get_tenant_complaints"
    ].passed is False
    assert checks["read-only investigation trace"].passed is False


@pytest.mark.parametrize(
    ("trace_mutation", "failed_check"),
    [
        (
            "telemetry_before_discovery",
            "sensor discovery result precedes telemetry",
        ),
        (
            "unknown_sensor_id",
            "telemetry sensor IDs came from discovery",
        ),
        (
            "unsupported_result_shape",
            "telemetry sensor IDs came from discovery",
        ),
    ],
)
def test_sensor_grounding_fails_for_unverified_telemetry(
    trace_mutation,
    failed_check,
):
    trace = create_grounded_trace()

    if trace_mutation == "telemetry_before_discovery":
        trace[1], trace[2] = trace[2], trace[1]
    elif trace_mutation == "unknown_sensor_id":
        trace[2].arguments["sensor_ids"].append("GUESSED-SENSOR")
    else:
        trace[1].content = json.dumps(
            {"sensor_ids": ["AHU01-HEAT-VALVE"]}
        )

    checks = checks_by_name(check_grounding(trace))

    assert checks[failed_check].passed is False


def test_investigation_requires_summary_telemetry_and_evidence_only():
    complete = check_investigation_completeness(
        create_investigation()
    )
    incomplete = check_investigation_completeness(
        OperationalInvestigation(
            summary=" ",
            telemetry_findings=[],
            maintenance_findings=[],
            occupant_impact=[],
            evidence=[],
        )
    )

    assert complete.passed is True
    assert incomplete.passed is False
    assert len(complete.checks) == 3


@pytest.mark.parametrize(
    "forbidden_text",
    [
        "Approve an actuator inspection.",
        "Seek approval before inspection.",
        "Authorize the repair.",
        "Request authorization for repair.",
        "Create a work order for inspection.",
        "Open a work-order for inspection.",
    ],
)
def test_assessment_rejects_control_language(forbidden_text):
    checks = checks_by_name(
        check_assessment_contract(
            create_assessment(
                recommended_next_step=forbidden_text
            )
        )
    )

    assert checks[
        "next step excludes approval/work-order control language"
    ].passed is False


def test_diagnostic_relevance_uses_concepts_not_exact_prose():
    relevant = check_assessment_contract(
        create_assessment(
            likely_issue="Possible control response problem.",
            recommended_next_step="Verify commanded and actual movement.",
        )
    )
    irrelevant = check_assessment_contract(
        create_assessment(
            likely_issue="Unexpected overnight energy use.",
            recommended_next_step="Review the overnight schedule.",
        )
    )

    assert relevant.passed is True
    assert checks_by_name(irrelevant)[
        "heating-valve diagnostic relevance"
    ].passed is False


def test_diagnostic_relevance_rejects_generic_heating_statement():
    assessment = create_assessment(
        likely_issue="Heating performance is abnormal",
        recommended_next_step="Review the available evidence.",
    )

    checks = checks_by_name(check_assessment_contract(assessment))

    assert checks[
        "heating-valve diagnostic relevance"
    ].passed is False


def test_confidence_range_remains_enforced_by_pydantic_model():
    data = create_assessment().model_dump()
    data["confidence"] = 1.1

    with pytest.raises(ValidationError):
        InvestigationAssessment.model_validate(data)


def test_rag_requires_results_and_attribution_fields():
    empty = create_rag().model_copy(update={"results": []})
    missing_text = create_rag()
    missing_text.results[0].text = " "

    assert check_rag(create_rag()).passed is True
    assert check_rag(empty).passed is False
    assert check_rag(missing_text).passed is False
