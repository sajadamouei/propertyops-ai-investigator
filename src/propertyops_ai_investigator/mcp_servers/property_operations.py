from pathlib import Path

import pandas as pd
from mcp.server import MCPServer

from propertyops_ai_investigator.domain.models import WorkOrder


WORK_ORDERS_PATH = Path("data/source/work_orders.csv")


mcp = MCPServer(
    "Property Operations",
    instructions=(
        "Provides read-only property operations and "
        "maintenance information."
    ),
)


@mcp.tool()
def get_work_orders(
    equipment_id: str,
) -> list[WorkOrder]:
    """Get historical maintenance work orders for equipment."""

    df = pd.read_csv(
        WORK_ORDERS_PATH,
        parse_dates=["created_at"],
    )

    matches = df[
        df["equipment_id"] == equipment_id
    ]

    return [
        WorkOrder(
            id=row["id"],
            building_id=row["building_id"],
            equipment_id=row["equipment_id"],
            created_at=row["created_at"].to_pydatetime(),
            description=row["description"],
            status=row["status"],
        )
        for _, row in matches.iterrows()
    ]


if __name__ == "__main__":
    mcp.run(transport="stdio")