# After-Hours AHU Operation Guide

Synthetic internal technical guidance for the PropertyOps AI Investigator demo.

## Unexpected operation

An air-handling unit running outside expected occupied hours should be investigated when fan operation and energy demand remain materially above the normal off-hours baseline.

The first step is to determine whether operation was intentionally requested or caused by an abnormal control condition.

## Scheduling and overrides

Check the building-management-system occupancy schedule, holiday calendar, temporary overrides, manual commands, and extended-hours requests.

A schedule or override problem can cause the fan, heating, and cooling systems to operate normally from the equipment perspective while still wasting energy because the building is unoccupied.

## Interaction with equipment faults

After-hours operation and an equipment fault can occur at the same time. For example, an AHU may be incorrectly scheduled to run while a heating valve or coil also fails to deliver the requested temperature.

Do not treat after-hours operation alone as proof that the scheduling system is the only problem.

## Recommended diagnostic sequence

Confirm the expected occupancy schedule, inspect active overrides, determine why the AHU was enabled, and then correlate the operating period with equipment telemetry and maintenance history.