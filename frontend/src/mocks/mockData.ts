import type {
  EvidenceItem,
  McpToolCall,
  OperationsView,
  PipelineStage,
  RagRetrieval,
  TelemetryPoint,
} from '../types'

export const telemetry: TelemetryPoint[] = [
  { timestamp: '2026-01-14T22:00:00', label: 'Jan 14, 22:00', powerKw: 29.1, heatingValvePct: 5.8, supplyAirTempC: 17.2, fanStatus: 0, anomalyScore: 0.42, isAnomaly: false },
  { timestamp: '2026-01-14T23:00:00', label: '23:00', powerKw: 27.6, heatingValvePct: 4.5, supplyAirTempC: 16.9, fanStatus: 0, anomalyScore: 0.39, isAnomaly: false },
  { timestamp: '2026-01-15T00:00:00', label: 'Jan 15, 00:00', powerKw: 30.2, heatingValvePct: 6.1, supplyAirTempC: 17.1, fanStatus: 0, anomalyScore: 0.44, isAnomaly: false },
  { timestamp: '2026-01-15T01:00:00', label: '01:00', powerKw: 143.8, heatingValvePct: 92.1, supplyAirTempC: 14.9, fanStatus: 1, anomalyScore: 0.6662, isAnomaly: true },
  { timestamp: '2026-01-15T02:00:00', label: '02:00', powerKw: 146.4, heatingValvePct: 93.7, supplyAirTempC: 14.7, fanStatus: 1, anomalyScore: 0.6841, isAnomaly: true },
  { timestamp: '2026-01-15T03:00:00', label: '03:00', powerKw: 148.7, heatingValvePct: 95.0, supplyAirTempC: 14.4, fanStatus: 1, anomalyScore: 0.6956, isAnomaly: true },
  { timestamp: '2026-01-15T04:00:00', label: '04:00', powerKw: 147.2, heatingValvePct: 94.4, supplyAirTempC: 14.6, fanStatus: 1, anomalyScore: 0.6889, isAnomaly: true },
  { timestamp: '2026-01-15T05:00:00', label: '05:00', powerKw: 141.1, heatingValvePct: 92.8, supplyAirTempC: 14.8, fanStatus: 1, anomalyScore: 0.6517, isAnomaly: true },
  { timestamp: '2026-01-15T06:00:00', label: '06:00', powerKw: 112.4, heatingValvePct: 39.2, supplyAirTempC: 18.1, fanStatus: 1, anomalyScore: 0.51, isAnomaly: false },
  { timestamp: '2026-01-15T07:00:00', label: '07:00', powerKw: 117.8, heatingValvePct: 36.9, supplyAirTempC: 18.7, fanStatus: 1, anomalyScore: 0.47, isAnomaly: false },
]

export const evidence: EvidenceItem[] = [
  { id: 'ev-t1', category: 'telemetry', title: 'After-hours power demand', detail: 'AHU power remained unusually high for five consecutive hours while the building was unoccupied.', value: '148.7 kW max', timestamp: '01:00–05:00' },
  { id: 'ev-t2', category: 'telemetry', title: 'Heating command did not produce heat', detail: 'The valve was nearly fully open while supply-air temperature continued to fall.', value: '95% / 14.4 °C', timestamp: '03:00' },
  { id: 'ev-t3', category: 'telemetry', title: 'Fan running out of schedule', detail: 'The supply fan ran continuously throughout the incident window.', value: '5 hours', timestamp: '01:00–05:00' },
  { id: 'ev-m1', category: 'maintenance', title: 'Previous actuator response issue', detail: 'WO-001: actuator calibration temporarily restored normal heating-valve operation.', value: 'Closed', timestamp: 'Nov 18, 2025' },
  { id: 'ev-o1', category: 'tenant', title: 'Cold office reported', detail: 'Office is unusually cold this morning.', value: 'ZONE-003', timestamp: '08:12' },
  { id: 'ev-o2', category: 'tenant', title: 'Third-floor meeting rooms cold', detail: 'Rooms feel much colder than normal.', value: 'ZONE-003', timestamp: '08:47' },
  { id: 'ev-o3', category: 'tenant', title: 'Cold air from ventilation', detail: 'Several employees reported cold supply air.', value: 'ZONE-003', timestamp: '09:21' },
]

export const operationsView: OperationsView = {
  incident: {
    id: 'INC-20260115-0100-AHU01',
    buildingId: 'BLDG-001',
    buildingName: 'Northpoint Offices',
    equipmentId: 'AHU-001',
    equipmentName: 'Main supply air handler',
    zoneId: 'ZONE-003',
    startedAt: '2026-01-15T01:00:00',
    endedAt: '2026-01-15T05:00:00',
    severity: 'high',
    anomalyScore: 0.6956,
    summary: 'Abnormal HVAC operating pattern detected for five consecutive hours.',
  },
  telemetry,
  evidence,
  complaintsCount: 3,
  investigationStatus: 'assessment_ready',
  assessment: {
    likelyIssue: 'Heating valve actuator or control schedule fault',
    confidence: 0.85,
    explanation: 'The heating valve was commanded almost fully open, yet supply air stayed cold while the fan and power draw remained high outside occupied hours. A prior actuator response issue makes a recurring control fault the leading explanation.',
    telemetryFindings: ['Power peaked at 148.7 kW outside occupied hours', 'Valve command reached 95% while supply air fell to 14.4 °C', 'Fan remained on for the full five-hour anomaly window'],
    maintenanceFindings: ['A November work order recorded intermittent actuator response', 'Calibration was documented as a temporary restoration'],
    occupantImpact: ['Three cold-comfort complaints followed in ZONE-003', 'Reports began at 08:12, shortly after occupancy started'],
    recommendedNextStep: 'Inspect the AHU-001 heating valve actuator and verify the overnight control schedule before replacing components.',
  },
  proposedWorkOrder: {
    title: 'Inspect AHU-001 heating valve controls',
    buildingId: 'BLDG-001',
    equipmentId: 'AHU-001',
    description: 'Inspect heating valve actuator response, verify linkage and calibration, and review the overnight fan and heating control schedule. Confirm supply-air temperature recovery after service.',
    priority: 'high',
    status: 'waiting',
  },
}

export const stageDefinitions: PipelineStage[] = [
  { id: 'generate', label: 'Generate Data', shortLabel: 'Generate', description: 'Create realistic property telemetry and inject the selected scenario.', status: 'ready' },
  { id: 'features', label: 'Feature Engineering', shortLabel: 'Features', description: 'Pivot sensor readings and add operating-context features.', status: 'not_started' },
  { id: 'detection', label: 'Anomaly Detection', shortLabel: 'Detection', description: 'Score each hour using the trained Isolation Forest.', status: 'not_started' },
  { id: 'incident', label: 'Build Incident', shortLabel: 'Incident', description: 'Group consecutive anomalies into an operational incident.', status: 'not_started' },
  { id: 'investigation', label: 'AI Investigation', shortLabel: 'Investigate', description: 'Collect telemetry, maintenance, and complaint evidence through MCP tools.', status: 'not_started' },
  { id: 'rag', label: 'RAG', shortLabel: 'RAG', description: 'Retrieve relevant operating and service documentation.', status: 'not_started' },
  { id: 'assessment', label: 'Assessment', shortLabel: 'Assess', description: 'Produce a structured, evidence-based assessment.', status: 'not_started' },
  { id: 'approval', label: 'Human Approval', shortLabel: 'Approval', description: 'Pause for an operator decision before any write action.', status: 'not_started' },
  { id: 'work-order', label: 'Work Order', shortLabel: 'Work order', description: 'Create the approved maintenance request.', status: 'not_started' },
]

export const mcpCalls: McpToolCall[] = [
  { id: 'call-1', name: 'get_equipment_sensors', purpose: 'Discover valid sensor IDs before querying readings', arguments: { equipment_id: 'AHU-001' }, resultSummary: '4 sensors: power, heating valve, supply temperature, fan status', status: 'complete' },
  { id: 'call-2', name: 'get_telemetry', purpose: 'Read the incident window using validated sensor IDs', arguments: { sensor_ids: ['AHU01-POWER', 'AHU01-HEAT-VALVE', 'AHU01-SUPPLY-TEMP', 'AHU01-FAN'], start: '2026-01-15T01:00:00Z', end: '2026-01-15T05:00:00Z' }, resultSummary: '20 readings returned across 4 sensors', status: 'complete' },
  { id: 'call-3', name: 'get_work_orders', purpose: 'Check AHU-001 maintenance history', arguments: { equipment_id: 'AHU-001' }, resultSummary: '2 closed work orders; one records intermittent actuator response', status: 'complete' },
  { id: 'call-4', name: 'get_tenant_complaints', purpose: 'Connect the event to occupant impact', arguments: { building_id: 'BLDG-001', zone_id: 'ZONE-003', start: '2026-01-15T06:00:00Z', end: '2026-01-15T12:00:00Z' }, resultSummary: '3 cold-comfort complaints returned', status: 'complete' },
]

export const ragRetrievals: RagRetrieval[] = [
  { id: 'rag-1', source: 'AHU Controls Handbook.pdf', section: '4.2 — Heating valve diagnostics', content: 'A high heating command paired with low downstream air temperature can indicate poor actuator travel, linkage slip, or unavailable heating medium. Confirm physical valve position before replacement.', score: 0.93 },
  { id: 'rag-2', source: 'BMS Sequence of Operations.pdf', section: '2.7 — Unoccupied mode', content: 'Supply fans should remain off during unoccupied mode except for frost protection or an authorized warm-up sequence. Overrides must be time-limited and logged.', score: 0.88 },
  { id: 'rag-3', source: 'Actuator Service Bulletin 24-08.pdf', section: 'Inspection procedure', content: 'For intermittent response, inspect the mechanical linkage and verify command-to-position calibration across the full operating range.', score: 0.84 },
]

export const rawTelemetryRows = telemetry.slice(2, 8).flatMap((point) => [
  { sensor: 'AHU01-POWER', timestamp: point.label, value: point.powerKw, unit: 'kW' },
  { sensor: 'AHU01-HEAT-VALVE', timestamp: point.label, value: point.heatingValvePct, unit: '%' },
  { sensor: 'AHU01-SUPPLY-TEMP', timestamp: point.label, value: point.supplyAirTempC, unit: '°C' },
])
