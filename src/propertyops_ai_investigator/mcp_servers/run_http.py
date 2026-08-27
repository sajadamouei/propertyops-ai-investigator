import os

from propertyops_ai_investigator.mcp_servers.property_operations import (
    mcp,
)


MCP_HOST = os.getenv(
    "PROPERTYOPS_MCP_HOST",
    "127.0.0.1",
)

MCP_PORT = int(
    os.getenv(
        "PROPERTYOPS_MCP_PORT",
        "8000",
    )
)


if __name__ == "__main__":
    mcp.run(
        transport="streamable-http",
        host=MCP_HOST,
        port=MCP_PORT,
        stateless_http=True,
        json_response=True,
    )