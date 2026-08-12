import asyncio

from mcp import Client

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
            result = await client.call_tool(
                "create_work_order",
                {
                    "building_id": "BLDG-001",
                    "equipment_id": "AHU-001",
                    "description": (
                        "Inspect heating valve actuator."
                    ),
                },
            )

            assert result.structured_content is not None

            content = result.structured_content

            assert content["created"] is True

            assert (
                content["work_order"]["status"]
                == "open"
            )

    asyncio.run(run_test())

    assert runtime_file.exists()

    contents = runtime_file.read_text(
        encoding="utf-8"
    )

    assert "Inspect heating valve actuator." in contents