from datetime import datetime
from pathlib import Path

import pandas as pd
from mcp.server import MCPServer

from propertyops_ai_investigator.domain.models import (
    SensorReading,
    TenantComplaint,
    WorkOrder,
)


WORK_ORDERS_PATH = Path("data/source/work_orders.csv")
COMPLAINTS_PATH = Path("data/source/tenant_complaints.csv")
TELEMETRY_PATH = Path("data/synthetic/sensor_readings.csv")


mcp = MCPServer(
    "Property Operations",
    instructions=(
        "Provides read-only access to building telemetry, "
        "tenant complaints, and maintenance history."
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


@mcp.tool()
def get_tenant_complaints(
    building_id: str,
    start: datetime,
    end: datetime,
    zone_id: str | None = None,
) -> list[TenantComplaint]:
    """Get tenant complaints within a time window."""

    df = pd.read_csv(
        COMPLAINTS_PATH,
        parse_dates=["timestamp"],
    )

    matches = df[
        (df["building_id"] == building_id)
        & (df["timestamp"] >= start)
        & (df["timestamp"] <= end)
    ]

    if zone_id is not None:
        matches = matches[
            matches["zone_id"] == zone_id
        ]

    return [
        TenantComplaint(
            id=row["id"],
            building_id=row["building_id"],
            zone_id=row["zone_id"],
            timestamp=row["timestamp"].to_pydatetime(),
            category=row["category"],
            description=row["description"],
        )
        for _, row in matches.iterrows()
    ]


@mcp.tool()
def get_telemetry(
    sensor_ids: list[str],
    start: datetime,
    end: datetime,
) -> list[SensorReading]:
    """Get sensor readings for selected sensors and time window."""

    df = pd.read_csv(
        TELEMETRY_PATH,
        parse_dates=["timestamp"],
    )

    matches = df[
        (df["sensor_id"].isin(sensor_ids))
        & (df["timestamp"] >= start)
        & (df["timestamp"] <= end)
    ]

    return [
        SensorReading(
            sensor_id=row["sensor_id"],
            timestamp=row["timestamp"].to_pydatetime(),
            value=float(row["value"]),
        )
        for _, row in matches.iterrows()
    ]


if __name__ == "__main__":
    mcp.run(transport="stdio")