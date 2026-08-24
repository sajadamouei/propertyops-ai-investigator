from datetime import datetime
from types import SimpleNamespace

from propertyops_ai_investigator.domain.models import (
    IncidentSeverity,
    OperationalIncident,
    TelemetryEvidence,
)
from propertyops_ai_investigator.services.investigation_service import (
    build_investigation_prompt,
    extract_tool_trace,
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