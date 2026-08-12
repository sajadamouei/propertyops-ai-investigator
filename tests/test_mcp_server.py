import asyncio

from mcp import Client

from propertyops_ai_investigator.mcp_servers.property_operations import (
    mcp,
)


def test_property_operations_mcp_tools():
    async def run_test():
        async with Client(mcp) as client:
            tools = await client.list_tools()

            tool_names = {
                tool.name
                for tool in tools.tools
            }

            assert {
                "get_work_orders",
                "get_tenant_complaints",
                "get_telemetry",
            }.issubset(tool_names)

            result = await client.call_tool(
                "get_work_orders",
                {
                    "equipment_id": "AHU-001",
                },
            )

            assert result.structured_content is not None
            assert len(
                result.structured_content["result"]
            ) == 2

    asyncio.run(run_test())