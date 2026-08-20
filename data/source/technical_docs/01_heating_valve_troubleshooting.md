# Heating Valve Troubleshooting Guide

Synthetic internal technical guidance for the PropertyOps AI Investigator demo.

## High command with low heating response

When a heating valve is commanded near fully open but supply-air temperature remains unexpectedly low, do not assume the actuator is the confirmed root cause. A high command signal only shows that the control system is requesting heat.

Compare the commanded valve position with the actual thermal response. Check whether supply-air temperature rises when heating demand increases.

## Mechanical checks

Inspect the heating valve actuator, linkage, and valve movement. Confirm that the actuator responds to control commands and that the mechanical linkage is not loose, stuck, or incorrectly calibrated.

A previous temporary improvement after actuator calibration is relevant evidence that the actuator or linkage should be inspected again, but it does not by itself confirm failure.

## Hydronic checks

Verify that hot water is available to the heating coil. Check upstream temperature, circulation, valves, and pumps where appropriate.

A fully commanded valve with poor thermal response can also occur when hot-water supply is unavailable or heat transfer through the coil is insufficient.

## Recommended diagnostic sequence

First verify control command and actual actuator movement. Then verify hot-water availability and heating-coil response. Avoid replacing components until the physical cause has been confirmed.