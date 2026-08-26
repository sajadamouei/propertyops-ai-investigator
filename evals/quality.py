"""Pure quality checks for the known heating-valve evaluation.

The checks deliberately inspect structured artifacts and the recorded MCP
trajectory.  They do not judge prose style and do not call an LLM.
"""

from collections.abc import Sequence
from dataclasses import dataclass
import json
import re

from propertyops_ai_investigator.domain.models import (
    InvestigationAssessment,
    OperationalInvestigation,
)
from propertyops_ai_investigator.services.investigation_service import (
    ToolTraceEntry,
)
from propertyops_ai_investigator.services.rag_service import (
    RagArtifact,
)


REQUIRED_INVESTIGATION_TOOLS = (
    "get_equipment_sensors",
    "get_telemetry",
    "get_work_orders",
    "get_tenant_complaints",
)

READ_ONLY_INVESTIGATION_TOOLS = frozenset(
    REQUIRED_INVESTIGATION_TOOLS
)

# This is intentionally a small concept family, not an exact-diagnosis list.
HEATING_VALVE_CONCEPTS = (
    "valve",
    "actuator",
    "control",
    "linkage",
)

_HEATING_VALVE_PATTERN = re.compile(
    r"\b(?:valve|actuator|control|linkage)\w*\b",
    re.IGNORECASE,
)

_CONTROL_LANGUAGE_PATTERN = re.compile(
    (
        r"\b(?:approve|approved|approval|authorize|authorized|"
        r"authorization|work[-\s]+orders?)\b"
    ),
    re.IGNORECASE,
)


@dataclass(frozen=True)
class QualityCheck:
    """One deterministic quality assertion."""

    name: str
    passed: bool
    detail: str


@dataclass(frozen=True)
class QualitySection:
    """A group of related quality assertions."""

    name: str
    checks: tuple[QualityCheck, ...]

    @property
    def passed(self) -> bool:
        return all(check.passed for check in self.checks)


@dataclass(frozen=True)
class AIQualityReport:
    """Deterministic report for one known incident scenario."""

    scenario: str
    grounding: QualitySection
    investigation_completeness: QualitySection
    assessment_contract: QualitySection
    rag: QualitySection

    @property
    def sections(self) -> tuple[QualitySection, ...]:
        return (
            self.grounding,
            self.investigation_completeness,
            self.assessment_contract,
            self.rag,
        )

    @property
    def passed(self) -> bool:
        return all(section.passed for section in self.sections)


def _has_text(value: str) -> bool:
    return bool(value.strip())


def _has_text_items(values: Sequence[str]) -> bool:
    return bool(values) and all(_has_text(value) for value in values)


def _trace_entries(
    trace: Sequence[ToolTraceEntry | dict],
) -> list[ToolTraceEntry]:
    return [
        ToolTraceEntry.model_validate(entry)
        for entry in trace
    ]


def _sensor_ids_from_discovery_result(
    content: str | None,
) -> set[str] | None:
    """Read the MCP server's documented ``{"result": [...]}`` shape.

    ``None`` means the trace content did not have the current MCP result
    format, so sensor-ID grounding cannot be established from that result.
    """

    if content is None:
        return None

    try:
        payload = json.loads(content)
    except (TypeError, json.JSONDecodeError):
        return None

    if not isinstance(payload, dict):
        return None

    results = payload.get("result")

    if not isinstance(results, list):
        return None

    sensor_ids: set[str] = set()

    for result in results:
        if not isinstance(result, dict):
            return None

        sensor_id = result.get("id")

        if not isinstance(sensor_id, str) or not sensor_id.strip():
            return None

        sensor_ids.add(sensor_id)

    return sensor_ids


def check_grounding(
    trace: Sequence[ToolTraceEntry | dict],
) -> QualitySection:
    """Check required evidence gathering, ordering, and read-only use."""

    entries = _trace_entries(trace)
    call_entries = [
        entry
        for entry in entries
        if entry.event == "tool_call"
    ]
    called_tools = {
        entry.tool_name
        for entry in call_entries
    }

    checks = [
        QualityCheck(
            name=f"required MCP call: {tool_name}",
            passed=tool_name in called_tools,
            detail=(
                "call recorded"
                if tool_name in called_tools
                else "call missing"
            ),
        )
        for tool_name in REQUIRED_INVESTIGATION_TOOLS
    ]

    unexpected_tools = sorted(
        called_tools - READ_ONLY_INVESTIGATION_TOOLS
    )
    checks.append(
        QualityCheck(
            name="read-only investigation trace",
            passed=not unexpected_tools,
            detail=(
                "only approved read tools were called"
                if not unexpected_tools
                else "non-read tool calls: " + ", ".join(unexpected_tools)
            ),
        )
    )

    discovered_ids: set[str] = set()
    saw_discovery_result = False
    telemetry_before_discovery = False
    ungrounded_requests: list[str] = []

    for entry in entries:
        if (
            entry.event == "tool_result"
            and entry.tool_name == "get_equipment_sensors"
        ):
            parsed_ids = _sensor_ids_from_discovery_result(
                entry.content
            )

            if parsed_ids is not None:
                saw_discovery_result = True
                discovered_ids.update(parsed_ids)

        if (
            entry.event != "tool_call"
            or entry.tool_name != "get_telemetry"
        ):
            continue

        if not saw_discovery_result:
            telemetry_before_discovery = True

        arguments = entry.arguments or {}
        requested_ids = arguments.get("sensor_ids")

        if (
            not isinstance(requested_ids, list)
            or not requested_ids
            or not all(
                isinstance(sensor_id, str)
                and bool(sensor_id.strip())
                for sensor_id in requested_ids
            )
        ):
            ungrounded_requests.append(
                "missing or invalid sensor_ids argument"
            )
            continue

        unknown_ids = sorted(
            set(requested_ids) - discovered_ids
        )

        if unknown_ids:
            ungrounded_requests.append(
                "undiscovered IDs: " + ", ".join(unknown_ids)
            )

    telemetry_calls = [
        entry
        for entry in call_entries
        if entry.tool_name == "get_telemetry"
    ]

    discovery_order_passed = (
        bool(telemetry_calls)
        and saw_discovery_result
        and not telemetry_before_discovery
    )
    checks.append(
        QualityCheck(
            name="sensor discovery result precedes telemetry",
            passed=discovery_order_passed,
            detail=(
                "a parseable discovery result preceded every telemetry call"
                if discovery_order_passed
                else "telemetry lacked a preceding parseable discovery result"
            ),
        )
    )

    sensor_ids_passed = (
        bool(telemetry_calls)
        and saw_discovery_result
        and not ungrounded_requests
    )
    checks.append(
        QualityCheck(
            name="telemetry sensor IDs came from discovery",
            passed=sensor_ids_passed,
            detail=(
                "all requested sensor IDs were discovered"
                if sensor_ids_passed
                else (
                    "; ".join(ungrounded_requests)
                    if ungrounded_requests
                    else "sensor IDs could not be verified from the trace"
                )
            ),
        )
    )

    return QualitySection(
        name="Grounding checks",
        checks=tuple(checks),
    )


def check_investigation_completeness(
    investigation: OperationalInvestigation,
) -> QualitySection:
    """Check only fields required for a complete investigation."""

    return QualitySection(
        name="Investigation completeness",
        checks=(
            QualityCheck(
                "summary is non-empty",
                _has_text(investigation.summary),
                "required investigation narrative",
            ),
            QualityCheck(
                "telemetry findings are non-empty",
                _has_text_items(investigation.telemetry_findings),
                "at least one non-empty telemetry finding is required",
            ),
            QualityCheck(
                "evidence is non-empty",
                _has_text_items(investigation.evidence),
                "at least one non-empty evidence item is required",
            ),
        ),
    )


def check_assessment_contract(
    assessment: InvestigationAssessment,
) -> QualitySection:
    """Check the structured assessment contract and fault relevance."""

    next_step = assessment.recommended_next_step
    forbidden_match = _CONTROL_LANGUAGE_PATTERN.search(next_step)
    diagnostic_text = (
        f"{assessment.likely_issue} {next_step}"
    )
    concept_match = _HEATING_VALVE_PATTERN.search(diagnostic_text)

    return QualitySection(
        name="Assessment contract",
        checks=(
            QualityCheck(
                "likely issue is non-empty",
                _has_text(assessment.likely_issue),
                "required assessment field",
            ),
            QualityCheck(
                "assessment evidence is non-empty",
                _has_text_items(assessment.evidence),
                "at least one non-empty evidence item is required",
            ),
            QualityCheck(
                "recommended next step is non-empty",
                _has_text(next_step),
                "required operational action",
            ),
            QualityCheck(
                "confidence is between 0 and 1",
                0 <= assessment.confidence <= 1,
                "validated through InvestigationAssessment",
            ),
            QualityCheck(
                "next step excludes approval/work-order control language",
                forbidden_match is None,
                (
                    "no control language found"
                    if forbidden_match is None
                    else f"forbidden phrase: {forbidden_match.group(0)!r}"
                ),
            ),
            QualityCheck(
                "heating-valve diagnostic relevance",
                concept_match is not None,
                (
                    f"matched concept: {concept_match.group(0).lower()}"
                    if concept_match is not None
                    else "none of the documented fault-family concepts appeared"
                ),
            ),
        ),
    )


def check_rag(rag: RagArtifact) -> QualitySection:
    """Check that retrieval returned attributable, non-empty chunks."""

    results_present = bool(rag.results)
    complete_results = results_present and all(
        _has_text(result.chunk_id)
        and _has_text(result.source)
        and _has_text(result.text)
        for result in rag.results
    )

    return QualitySection(
        name="RAG checks",
        checks=(
            QualityCheck(
                "RAG results are non-empty",
                results_present,
                f"{len(rag.results)} result(s)",
            ),
            QualityCheck(
                "each RAG result has chunk_id, source, and text",
                complete_results,
                (
                    "all result attribution fields are non-empty"
                    if complete_results
                    else "one or more results lack required attribution"
                ),
            ),
        ),
    )


def evaluate_heating_valve_quality(
    investigation: OperationalInvestigation,
    trace: Sequence[ToolTraceEntry | dict],
    assessment: InvestigationAssessment,
    rag: RagArtifact,
) -> AIQualityReport:
    """Evaluate artifacts from the known Heating Valve Fault scenario."""

    return AIQualityReport(
        scenario="Heating Valve Fault",
        grounding=check_grounding(trace),
        investigation_completeness=(
            check_investigation_completeness(investigation)
        ),
        assessment_contract=check_assessment_contract(assessment),
        rag=check_rag(rag),
    )
