import pandas as pd

from propertyops_ai_investigator.domain.models import (
    IncidentSeverity,
    OperationalIncident,
    TelemetryEvidence,
)


def determine_severity(points: int) -> IncidentSeverity:
    if points >= 4:
        return IncidentSeverity.HIGH

    if points >= 2:
        return IncidentSeverity.MEDIUM

    return IncidentSeverity.LOW


def create_operational_incidents(
    scored: pd.DataFrame,
    events: pd.DataFrame,
) -> list[OperationalIncident]:
    incidents: list[OperationalIncident] = []

    for _, event in events.iterrows():
        start = pd.Timestamp(event["start"])
        end = pd.Timestamp(event["end"])

        window = scored[
            (scored["timestamp"] >= start)
            & (scored["timestamp"] <= end)
        ]

        points = int(event["points"])

        incident = OperationalIncident(
            id=f"INC-{start:%Y%m%d-%H%M}-AHU01",
            building_id="BLDG-001",
            equipment_id="AHU-001",
            started_at=start.to_pydatetime(),
            ended_at=end.to_pydatetime(),
            severity=determine_severity(points),
            anomaly_score=float(event["max_anomaly_score"]),
            summary=(
                "Abnormal HVAC operating pattern detected "
                f"for {points} consecutive hours."
            ),
            evidence=[
                TelemetryEvidence(
                    metric="power_kw",
                    value=float(window["power_kw"].max()),
                    unit="kW",
                    aggregation="max",
                ),
                TelemetryEvidence(
                    metric="heating_valve_pct",
                    value=float(
                        window["heating_valve_pct"].max()
                    ),
                    unit="%",
                    aggregation="max",
                ),
                TelemetryEvidence(
                    metric="supply_air_temp_c",
                    value=float(
                        window["supply_air_temp_c"].min()
                    ),
                    unit="C",
                    aggregation="min",
                ),
                TelemetryEvidence(
                    metric="fan_status",
                    value=float(window["fan_status"].max()),
                    unit=None,
                    aggregation="max",
                ),
            ],
        )

        incidents.append(incident)

    return incidents