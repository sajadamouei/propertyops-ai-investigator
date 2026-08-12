import asyncio

from mcp import Client


MCP_URL = "http://127.0.0.1:8000/mcp"


async def main() -> None:
    async with Client(MCP_URL) as client:
        tools = await client.list_tools()

        print("Remote MCP tools:")

        for tool in tools.tools:
            print(f"- {tool.name}")

        result = await client.call_tool(
            "get_work_orders",
            {
                "equipment_id": "AHU-001",
            },
        )

        print()
        print("Remote tool result:")
        print(result.structured_content)


if __name__ == "__main__":
    asyncio.run(main())