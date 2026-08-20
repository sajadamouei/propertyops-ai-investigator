from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, model_validator


class ScenarioType(str, Enum):
    NORMAL_OPERATION = "normal_operation"
    HEATING_VALVE_FAULT = "heating_valve_fault"
    CUSTOM_FAULT = "custom_fault"


class FaultType(str, Enum):
    SPIKE = "spike"
    MULTIPLIER = "multiplier"
    OFFSET = "offset"
    STUCK = "stuck"
    MISSING = "missing"


class FaultSpec(BaseModel):
    sensor_id: str
    fault_type: FaultType
    start: datetime
    end: datetime

    value: float | None = None

    @model_validator(mode="after")
    def validate_fault(self):
        if self.end <= self.start:
            raise ValueError(
                "Fault end must be after fault start."
            )

        if (
            self.fault_type != FaultType.MISSING
            and self.value is None
        ):
            raise ValueError(
                f"{self.fault_type.value} fault requires a value."
            )

        return self


class ExperimentConfig(BaseModel):
    scenario: ScenarioType

    days: int = Field(
        default=14,
        ge=1,
        le=60,
    )

    seed: int = Field(
        default=42,
        ge=0,
    )

    start_at: datetime = datetime(
        2026,
        1,
        5,
        0,
        0,
    )

    faults: list[FaultSpec] = Field(
        default_factory=list
    )

def create_scenario_config(
    scenario: ScenarioType,
    *,
    days: int = 14,
    seed: int = 42,
) -> ExperimentConfig:
    if scenario == ScenarioType.NORMAL_OPERATION:
        return ExperimentConfig(
            scenario=scenario,
            days=days,
            seed=seed,
            faults=[],
        )

    if scenario == ScenarioType.HEATING_VALVE_FAULT:
        return ExperimentConfig(
            scenario=scenario,
            days=days,
            seed=seed,
            faults=[
                FaultSpec(
                    sensor_id="AHU01-FAN",
                    fault_type=FaultType.STUCK,
                    start=datetime(2026, 1, 15, 1),
                    end=datetime(2026, 1, 15, 5),
                    value=1.0,
                    ),
                FaultSpec(
                    sensor_id="AHU01-POWER",
                    fault_type=FaultType.OFFSET,
                    start=datetime(2026, 1, 15, 1),
                    end=datetime(2026, 1, 15, 5),
                    value=117.0,
                ),
                FaultSpec(
                    sensor_id="AHU01-HEAT-VALVE",
                    fault_type=FaultType.OFFSET,
                    start=datetime(2026, 1, 15, 1),
                    end=datetime(2026, 1, 15, 5),
                    value=87.0,
                ),
                FaultSpec(
                    sensor_id="AHU01-SUPPLY-TEMP",
                    fault_type=FaultType.OFFSET,
                    start=datetime(2026, 1, 15, 1),
                    end=datetime(2026, 1, 15, 5),
                    value=-2.5,
                ),
                FaultSpec(
                    sensor_id="ZONE03-TEMP",
                    fault_type=FaultType.OFFSET,
                    start=datetime(2026, 1, 15, 6),
                    end=datetime(2026, 1, 15, 10),
                    value=-2.9,
                ),
            ],
        )

    return ExperimentConfig(
        scenario=ScenarioType.CUSTOM_FAULT,
        days=days,
        seed=seed,
        faults=[],
    )