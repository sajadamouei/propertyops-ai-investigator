import asyncio
import csv

from mcp import Client
import pytest

import propertyops_ai_investigator.mcp_servers.property_operations as operations


def test_property_operations_mcp_tools():
    async def run_test():
        async with Client(operations.mcp) as client:
            # 1. Check that expected MCP tools are exposed.
            tools = await client.list_tools()

            tools_by_name = {
                tool.name: tool
                for tool in tools.tools
            }

            assert {
                "get_equipment_sensors",
                "get_work_orders",
                "get_tenant_complaints",
                "get_telemetry",
                "create_work_order",
            }.issubset(tools_by_name)

            # 2. Check read/write safety metadata.
            assert (
                tools_by_name[
                    "get_work_orders"
                ].annotations.read_only_hint
                is True
            )

            assert (
                tools_by_name[
                    "create_work_order"
                ].annotations.read_only_hint
                is False
            )

            assert (
                tools_by_name[
                    "create_work_order"
                ].annotations.idempotent_hint
                is True
            )

            # 3. Check sensor discovery.
            sensors = await client.call_tool(
                "get_equipment_sensors",
                {
                    "equipment_id": "AHU-001",
                },
            )

            assert sensors.structured_content is not None

            sensor_ids = {
                sensor["id"]
                for sensor in sensors.structured_content["result"]
            }

            assert {
                "AHU01-POWER",
                "AHU01-HEAT-VALVE",
                "AHU01-SUPPLY-TEMP",
                "AHU01-FAN",
            }.issubset(sensor_ids)

            # 4. Check timezone-aware complaint query.
            complaints = await client.call_tool(
                "get_tenant_complaints",
                {
                    "building_id": "BLDG-001",
                    "zone_id": "ZONE-003",
                    "start": "2026-01-15T06:00:00Z",
                    "end": "2026-01-15T12:00:00Z",
                },
            )

            assert complaints.structured_content is not None

            assert len(
                complaints.structured_content["result"]
            ) == 3

    asyncio.run(run_test())


def test_create_work_order_through_mcp(
    tmp_path,
    monkeypatch,
):
    runtime_file = tmp_path / "created_work_orders.csv"

    monkeypatch.setattr(
        operations,
        "RUNTIME_WORK_ORDERS_PATH",
        runtime_file,
    )

    async def run_test():
        async with Client(operations.mcp) as client:
            arguments = {
                "building_id": "BLDG-001",
                "equipment_id": "AHU-001",
                "description": (
                    "Inspect heating valve actuator."
                ),
                "idempotency_key": (
                    "test-run:INC-TEST:work_order"
                ),
            }

            first_result = await client.call_tool(
                "create_work_order",
                arguments,
            )

            second_result = await client.call_tool(
                "create_work_order",
                arguments,
            )

            assert (
                first_result.structured_content
                is not None
            )
            assert (
                second_result.structured_content
                is not None
            )

            first_content = (
                first_result.structured_content
            )
            second_content = (
                second_result.structured_content
            )

            assert first_content["created"] is True
            assert second_content["created"] is True

            assert (
                first_content["work_order"]["status"]
                == "open"
            )

            assert (
                first_content["work_order"]["id"]
                == second_content["work_order"]["id"]
            )

    asyncio.run(run_test())

    assert runtime_file.exists()

    with runtime_file.open(
        "r",
        newline="",
        encoding="utf-8",
    ) as file:
        rows = list(csv.DictReader(file))

    assert len(rows) == 1

    assert (
        rows[0]["description"]
        == "Inspect heating valve actuator."
    )


def test_create_work_order_rejects_reused_key_for_new_payload(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(
        operations,
        "RUNTIME_WORK_ORDERS_PATH",
        tmp_path / "created_work_orders.csv",
    )

    arguments = {
        "building_id": "BLDG-001",
        "equipment_id": "AHU-001",
        "description": (
            "Inspect heating valve actuator."
        ),
        "idempotency_key": (
            "test-run:INC-TEST:work_order"
        ),
    }

    operations.create_work_order(
        **arguments
    )

    with pytest.raises(
        ValueError,
        match=(
            "Idempotency key was reused for a "
            "different work-order request"
        ),
    ):
        operations.create_work_order(
            **{
                **arguments,
                "description": (
                    "Replace heating valve actuator."
                ),
            }
        )


def test_create_work_order_rejects_empty_idempotency_key(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(
        operations,
        "RUNTIME_WORK_ORDERS_PATH",
        tmp_path / "created_work_orders.csv",
    )

    with pytest.raises(
        ValueError,
        match="idempotency_key must not be empty",
    ):
        operations.create_work_order(
            building_id="BLDG-001",
            equipment_id="AHU-001",
            description=(
                "Inspect heating valve actuator."
            ),
            idempotency_key="   ",
        )
