from propertyops_ai_investigator.mcp_servers.property_operations import (
    mcp,
)


if __name__ == "__main__":
    mcp.run(
        transport="streamable-http",
        host="127.0.0.1",
        port=8000,
        stateless_http=True,
        json_response=True,
    )