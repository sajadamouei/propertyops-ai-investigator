import os

from mcp import Client
from langchain_core.tools import tool


MCP_URL = os.getenv(
    "PROPERTYOPS_MCP_URL",
    "http://127.0.0.1:8000/mcp",
)


async def call_mcp_tool(
    tool_name: str,
    arguments: dict,
) -> dict:
    async with Client(MCP_URL) as client:
        result = await client.call_tool(
            tool_name,
            arguments,
        )

    return result.structured_content or {}


@tool
async def get_work_orders(
    equipment_id: str,
) -> dict:
    """Get maintenance history for equipment."""

    return await call_mcp_tool(
        "get_work_orders",
        {
            "equipment_id": equipment_id,
        },
    )


@tool
async def get_tenant_complaints(
    building_id: str,
    start: str,
    end: str,
    zone_id: str | None = None,
) -> dict:
    """Get tenant complaints in an ISO-8601 time window."""

    arguments = {
        "building_id": building_id,
        "start": start,
        "end": end,
    }

    if zone_id is not None:
        arguments["zone_id"] = zone_id

    return await call_mcp_tool(
        "get_tenant_complaints",
        arguments,
    )


@tool
async def get_telemetry(
    sensor_ids: list[str],
    start: str,
    end: str,
) -> dict:
    """Get building telemetry for sensors in an ISO-8601 time window."""

    return await call_mcp_tool(
        "get_telemetry",
        {
            "sensor_ids": sensor_ids,
            "start": start,
            "end": end,
        },
    )

@tool
async def get_equipment_sensors(
    equipment_id: str,
) -> dict:
    """List valid sensor IDs available for equipment."""

    return await call_mcp_tool(
        "get_equipment_sensors",
        {
            "equipment_id": equipment_id,
        },
    )


READ_TOOLS = [
    get_equipment_sensors,
    get_work_orders,
    get_tenant_complaints,
    get_telemetry,
]