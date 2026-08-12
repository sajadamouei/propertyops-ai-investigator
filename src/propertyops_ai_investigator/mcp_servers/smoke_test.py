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
            print(
                f"- {tool.name}: "
                f"{tool.description}"
            )

        result = await client.call_tool(
            "get_work_orders",
            {
                "equipment_id": "AHU-001",
            },
        )

        print()
        print("Tool result:")
        print(result.structured_content)


if __name__ == "__main__":
    asyncio.run(main())