from fastapi.testclient import TestClient

from propertyops_ai_investigator.api.main import (
    app,
)


client = TestClient(app)


def heating_fault_payload() -> dict:
    return {
        "scenario": "heating_valve_fault",
        "days": 14,
        "seed": 42,
    }


def test_health():
    response = client.get(
        "/api/health"
    )

    assert response.status_code == 200

    assert response.json() == {
        "status": "ok"
    }


def test_heating_fault_pipeline_through_api():
    response = client.post(
        "/api/runs/reset",
        json=heating_fault_payload(),
    )

    assert response.status_code == 200

    assert (
        client.post(
            "/api/pipeline/generate"
        ).status_code
        == 200
    )

    assert (
        client.post(
            "/api/pipeline/features"
        ).status_code
        == 200
    )

    detection = client.post(
        "/api/pipeline/detect"
    )

    assert detection.status_code == 200

    detection_data = detection.json()

    assert (
        detection_data[
            "event_count"
        ]
        == 1
    )

    incident = client.post(
        "/api/pipeline/incident"
    )

    assert incident.status_code == 200

    incident_data = (
        incident.json()["incident"]
    )

    assert incident_data is not None

    assert (
        incident_data["equipment_id"]
        == "AHU-001"
    )


def test_artifact_endpoint_returns_rows():
    reset_response = client.post(
        "/api/runs/reset",
        json=heating_fault_payload(),
    )

    assert reset_response.status_code == 200

    generate_response = client.post(
        "/api/pipeline/generate"
    )

    assert generate_response.status_code == 200

    response = client.get(
        "/api/artifacts/raw-telemetry",
        params={
            "limit": 5,
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["total_rows"] == 1680
    assert len(data["rows"]) == 5


def test_pipeline_rejects_out_of_order_step():
    reset_response = client.post(
        "/api/runs/reset",
        json={
            "scenario": "normal_operation",
            "days": 14,
            "seed": 42,
        },
    )

    assert reset_response.status_code == 200

    response = client.post(
        "/api/pipeline/features"
    )

    assert response.status_code == 400

    assert (
        "raw_telemetry.csv"
        in response.json()["detail"]
    )