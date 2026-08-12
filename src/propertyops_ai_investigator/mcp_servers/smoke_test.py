import asyncio

from mcp import Client

from propertyops_ai_investigator.mcp_servers.property_operations import (
    mcp,
)


async def main() -> None:
    async with Client(mcp) as client:
        tools = await client.list_tools()

        print("Available tools:")

        for tool in tools.tools:
            print(f"- {tool.name}: {tool.description}")

        print()
        print("Maintenance history:")

        work_orders = await client.call_tool(
            "get_work_orders",
            {
                "equipment_id": "AHU-001",
            },
        )

        print(work_orders.structured_content)

        print()
        print("Tenant complaints:")

        complaints = await client.call_tool(
            "get_tenant_complaints",
            {
                "building_id": "BLDG-001",
                "zone_id": "ZONE-003",
                "start": "2026-01-15T06:00:00",
                "end": "2026-01-15T12:00:00",
            },
        )

        print(complaints.structured_content)

        print()
        print("Incident telemetry:")

        telemetry = await client.call_tool(
            "get_telemetry",
            {
                "sensor_ids": [
                    "AHU01-POWER",
                    "AHU01-HEAT-VALVE",
                    "AHU01-SUPPLY-TEMP",
                ],
                "start": "2026-01-15T01:00:00",
                "end": "2026-01-15T05:00:00",
            },
        )

        print(telemetry.structured_content)


if __name__ == "__main__":
    asyncio.run(main())