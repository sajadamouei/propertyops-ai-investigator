import asyncio
from datetime import datetime
from types import SimpleNamespace

import pytest

from propertyops_ai_investigator.services import (
    investigation_service,
)
from propertyops_ai_investigator.data.experiment import (
    ExperimentConfig,
    ScenarioType,
)
from propertyops_ai_investigator.domain.models import (
    IncidentSeverity,
    OperationalIncident,
    OperationalInvestigation,
    TelemetryEvidence,
)
from propertyops_ai_investigator.services.ai_timeout import (
    AI_STAGE_TIMEOUT_SECONDS,
)
from propertyops_ai_investigator.services.investigation_service import (
    McpInvestigationService,
    build_investigation_prompt,
    extract_tool_trace,
)
from propertyops_ai_investigator.services.workspace import (
    INVESTIGATION_FILE,
    MCP_TRACE_FILE,
    PipelineStep,
    RunManifest,
    RunStatus,
    load_manifest,
    save_manifest,
)


def create_test_incident():
    return OperationalIncident(
        id="INC-TEST",
        building_id="BLDG-001",
        equipment_id="AHU-001",
        started_at=datetime(
            2026,
            1,
            15,
            1,
        ),
        ended_at=datetime(
            2026,
            1,
            15,
            5,
        ),
        severity=IncidentSeverity.HIGH,
        anomaly_score=0.69,
        summary="Test HVAC incident.",
        evidence=[
            TelemetryEvidence(
                metric="power_kw",
                value=148.3,
                unit="kW",
                aggregation="max",
            ),
            TelemetryEvidence(
                metric="heating_valve_pct",
                value=93.2,
                unit="%",
                aggregation="max",
            ),
            TelemetryEvidence(
                metric="supply_air_temp_c",
                value=13.9,
                unit="C",
                aggregation="min",
            ),
        ],
    )


def create_test_manifest(tmp_path):
    save_manifest(
        RunManifest(
            run_id="test-run",
            config=ExperimentConfig(
                scenario=(
                    ScenarioType.NORMAL_OPERATION
                ),
            ),
        ),
        tmp_path,
    )


def test_investigation_prompt_contains_required_context():
    prompt = build_investigation_prompt(
        create_test_incident()
    )

    assert "AHU-001" in prompt
    assert "BLDG-001" in prompt

    assert (
        "discover the valid sensor IDs"
        in prompt
    )

    assert (
        "2026-01-15T06:00:00"
        in prompt
    )

    assert (
        "2026-01-15T12:00:00"
        in prompt
    )

    assert (
        "Do not perform write actions"
        in prompt
    )


def test_extract_tool_trace():
    messages = [
        SimpleNamespace(
            type="ai",
            tool_calls=[
                {
                    "name": (
                        "get_equipment_sensors"
                    ),
                    "args": {
                        "equipment_id": (
                            "AHU-001"
                        ),
                    },
                    "id": "call-1",
                }
            ],
        ),
        SimpleNamespace(
            type="tool",
            tool_calls=None,
            name="get_equipment_sensors",
            tool_call_id="call-1",
            content=(
                '{"sensor_ids": '
                '["AHU01-POWER"]}'
            ),
        ),
        SimpleNamespace(
            type="ai",
            tool_calls=[
                {
                    "name": (
                        "OperationalInvestigation"
                    ),
                    "args": {
                        "summary": "test",
                    },
                    "id": "structured-1",
                }
            ],
        ),
        SimpleNamespace(
            type="tool",
            tool_calls=None,
            name="OperationalInvestigation",
            tool_call_id="structured-1",
            content="Returning structured response",
        ),
    ]

    trace = extract_tool_trace(
        messages
    )

    assert len(trace) == 2

    assert trace[0].event == "tool_call"

    assert (
        trace[0].tool_name
        == "get_equipment_sensors"
    )

    assert trace[1].event == "tool_result"

    assert (
        trace[1].tool_call_id
        == "call-1"
    )


@pytest.mark.anyio
async def test_investigation_success_remains_unchanged(
    tmp_path,
    monkeypatch,
):
    create_test_manifest(tmp_path)

    expected = OperationalInvestigation(
        summary="Operational evidence gathered.",
        telemetry_findings=[
            "Heating valve was highly open."
        ],
        maintenance_findings=[
            "Previous actuator calibration."
        ],
        occupant_impact=[
            "Cold comfort complaints."
        ],
        evidence=[
            "Telemetry and records retrieved."
        ],
    )

    class FakeAgent:
        async def ainvoke(self, request):
            assert "messages" in request
            return {
                "structured_response": expected,
                "messages": [],
            }

    monkeypatch.setattr(
        investigation_service,
        "ChatGoogleGenerativeAI",
        lambda **kwargs: object(),
    )
    monkeypatch.setattr(
        investigation_service,
        "create_agent",
        lambda **kwargs: FakeAgent(),
    )

    service = McpInvestigationService(
        tmp_path
    )

    assert (
        service.ai_timeout_seconds
        == AI_STAGE_TIMEOUT_SECONDS
        == 60.0
    )

    artifact = await service.run(
        create_test_incident()
    )

    assert artifact.investigation == expected
    assert artifact.trace == []
    assert (
        tmp_path / INVESTIGATION_FILE
    ).exists()
    assert (
        tmp_path / MCP_TRACE_FILE
    ).exists()

    manifest = load_manifest(tmp_path)
    assert manifest.status == RunStatus.READY
    assert manifest.current_step is None
    assert (
        PipelineStep.AI_INVESTIGATION
        in manifest.completed_steps
    )


@pytest.mark.anyio
async def test_investigation_timeout_marks_failed_and_propagates(
    tmp_path,
    monkeypatch,
):
    create_test_manifest(tmp_path)

    class HangingAgent:
        async def ainvoke(self, request):
            await asyncio.Event().wait()

    monkeypatch.setattr(
        investigation_service,
        "ChatGoogleGenerativeAI",
        lambda **kwargs: object(),
    )
    monkeypatch.setattr(
        investigation_service,
        "create_agent",
        lambda **kwargs: HangingAgent(),
    )

    with pytest.raises(TimeoutError):
        await McpInvestigationService(
            tmp_path,
            ai_timeout_seconds=0.001,
        ).run(
            create_test_incident()
        )

    manifest = load_manifest(tmp_path)
    assert manifest.status == RunStatus.FAILED
    assert (
        manifest.current_step
        == PipelineStep.AI_INVESTIGATION
    )
    assert (
        PipelineStep.AI_INVESTIGATION
        not in manifest.completed_steps
    )
    assert not (
        tmp_path / INVESTIGATION_FILE
    ).exists()
