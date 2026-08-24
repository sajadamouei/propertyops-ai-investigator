from datetime import datetime
from pathlib import Path
import csv
from hashlib import sha256
from threading import Lock

import pandas as pd
from mcp.server import MCPServer
from mcp.types import ToolAnnotations

from propertyops_ai_investigator.domain.models import (
    Sensor,
    SensorReading,
    TenantComplaint,
    WorkOrder,
    WorkOrderCreationResult,
    WorkOrderStatus,
)


WORK_ORDERS_PATH = Path("data/source/work_orders.csv")
COMPLAINTS_PATH = Path("data/source/tenant_complaints.csv")
TELEMETRY_PATH = Path("data/synthetic/sensor_readings.csv")
SENSORS_PATH = Path("data/source/sensors.csv")

RUNTIME_WORK_ORDERS_PATH = Path(
    "data/runtime/created_work_orders.csv"
)

CREATE_WORK_ORDER_LOCK = Lock()


def normalize_timestamp(
    value: datetime,
) -> pd.Timestamp:
    timestamp = pd.Timestamp(value)

    if timestamp.tzinfo is None:
        return timestamp.tz_localize("UTC")

    return timestamp.tz_convert("UTC")


mcp = MCPServer(
    "Property Operations",
    instructions=(
        "Provides access to building telemetry, equipment sensors, "
        "tenant complaints, maintenance history, and maintenance actions."
    ),
)


@mcp.tool(
    annotations=ToolAnnotations(
        readOnlyHint=True,
        idempotentHint=True,
        openWorldHint=False,
    )
)
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


@mcp.tool(
    annotations=ToolAnnotations(
        readOnlyHint=True,
        idempotentHint=True,
        openWorldHint=False,
    )
)
def get_equipment_sensors(
    equipment_id: str,
) -> list[Sensor]:
    """List valid sensors available for equipment."""

    df = pd.read_csv(
        SENSORS_PATH,
        keep_default_na=False,
    )

    matches = df[
        df["equipment_id"] == equipment_id
    ]

    return [
        Sensor(
            id=row["sensor_id"],
            equipment_id=row["equipment_id"] or None,
            zone_id=row["zone_id"] or None,
            sensor_type=row["sensor_type"],
            unit=row["unit"],
        )
        for _, row in matches.iterrows()
    ]


@mcp.tool(
    annotations=ToolAnnotations(
        readOnlyHint=True,
        idempotentHint=True,
        openWorldHint=False,
    )
)
def get_tenant_complaints(
    building_id: str,
    start: datetime,
    end: datetime,
    zone_id: str | None = None,
) -> list[TenantComplaint]:
    """Get tenant complaints within a time window."""

    df = pd.read_csv(COMPLAINTS_PATH)

    df["timestamp"] = pd.to_datetime(
        df["timestamp"],
        utc=True,
    )

    start_timestamp = normalize_timestamp(start)
    end_timestamp = normalize_timestamp(end)

    matches = df[
        (df["building_id"] == building_id)
        & (df["timestamp"] >= start_timestamp)
        & (df["timestamp"] <= end_timestamp)
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


@mcp.tool(
    annotations=ToolAnnotations(
        readOnlyHint=True,
        idempotentHint=True,
        openWorldHint=False,
    )
)
def get_telemetry(
    sensor_ids: list[str],
    start: datetime,
    end: datetime,
) -> list[SensorReading]:
    """Get sensor readings for selected sensors and time window."""

    df = pd.read_csv(TELEMETRY_PATH)

    df["timestamp"] = pd.to_datetime(
        df["timestamp"],
        utc=True,
    )

    start_timestamp = normalize_timestamp(start)
    end_timestamp = normalize_timestamp(end)

    matches = df[
        (df["sensor_id"].isin(sensor_ids))
        & (df["timestamp"] >= start_timestamp)
        & (df["timestamp"] <= end_timestamp)
    ]

    return [
        SensorReading(
            sensor_id=row["sensor_id"],
            timestamp=row["timestamp"].to_pydatetime(),
            value=float(row["value"]),
        )
        for _, row in matches.iterrows()
    ]


@mcp.tool(
    annotations=ToolAnnotations(
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    )
)
def create_work_order(
    building_id: str,
    equipment_id: str,
    description: str,
    idempotency_key: str,
) -> WorkOrderCreationResult:
    """Create a maintenance work order.

    This changes application state and should only be called
    after explicit user approval.
    """

    if not idempotency_key.strip():
        raise ValueError(
            "idempotency_key must not be empty."
        )

    digest = sha256(
        idempotency_key.encode("utf-8")
    ).hexdigest().upper()
    work_order_id = f"WO-{digest[:16]}"

    with CREATE_WORK_ORDER_LOCK:
        RUNTIME_WORK_ORDERS_PATH.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        if RUNTIME_WORK_ORDERS_PATH.exists():
            with RUNTIME_WORK_ORDERS_PATH.open(
                "r",
                newline="",
                encoding="utf-8",
            ) as file:
                for row in csv.DictReader(file):
                    if row["id"] != work_order_id:
                        continue

                    if (
                        row["building_id"]
                        != building_id
                        or row["equipment_id"]
                        != equipment_id
                        or row["description"]
                        != description
                    ):
                        raise ValueError(
                            "Idempotency key was reused "
                            "for a different work-order "
                            "request."
                        )

                    existing_work_order = (
                        WorkOrder.model_validate(row)
                    )

                    return WorkOrderCreationResult(
                        created=True,
                        work_order=(
                            existing_work_order
                        ),
                    )

        work_order = WorkOrder(
            id=work_order_id,
            building_id=building_id,
            equipment_id=equipment_id,
            created_at=datetime.now(),
            description=description,
            status=WorkOrderStatus.OPEN,
        )

        file_exists = (
            RUNTIME_WORK_ORDERS_PATH.exists()
        )

        with RUNTIME_WORK_ORDERS_PATH.open(
            "a",
            newline="",
            encoding="utf-8",
        ) as file:
            writer = csv.DictWriter(
                file,
                fieldnames=[
                    "id",
                    "building_id",
                    "equipment_id",
                    "created_at",
                    "description",
                    "status",
                ],
            )

            if not file_exists:
                writer.writeheader()

            writer.writerow(
                {
                    "id": work_order.id,
                    "building_id": (
                        work_order.building_id
                    ),
                    "equipment_id": (
                        work_order.equipment_id
                    ),
                    "created_at": (
                        work_order.created_at
                        .isoformat()
                    ),
                    "description": (
                        work_order.description
                    ),
                    "status": (
                        work_order.status.value
                    ),
                }
            )

        return WorkOrderCreationResult(
            created=True,
            work_order=work_order,
        )


if __name__ == "__main__":
    mcp.run(
        transport="stdio",
    )
