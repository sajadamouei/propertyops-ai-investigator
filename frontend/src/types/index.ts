export type PipelineStageId =
  | 'generate'
  | 'features'
  | 'detection'
  | 'incident'
  | 'investigation'
  | 'rag'
  | 'assessment'
  | 'approval'
  | 'work-order'

export type PipelineStageStatus =
  | 'not_started'
  | 'ready'
  | 'running'
  | 'complete'
  | 'waiting'
  | 'skipped'
  | 'failed'

export interface PipelineStage {
  id: PipelineStageId
  label: string
  shortLabel: string
  description: string
  status: PipelineStageStatus
}

export type ExperimentScenario = 'fault' | 'normal' | 'custom'
export type FaultType = 'spike' | 'multiplier' | 'offset' | 'stuck' | 'missing'

export interface FaultSpec {
  sensorId: string
  start: string
  end: string
  type: FaultType
  value: number
}

export interface ExperimentConfig {
  scenario: ExperimentScenario
  days: number
  randomSeed: number
  customFault: FaultSpec
}

export interface TelemetryPoint {
  timestamp: string
  label: string
  powerKw: number
  heatingValvePct: number
  supplyAirTempC: number
  fanStatus: number
  anomalyScore: number
  isAnomaly: boolean
}

export interface EvidenceItem {
  id: string
  category: 'telemetry' | 'maintenance' | 'tenant'
  title: string
  detail: string
  value?: string
  timestamp?: string
}

export interface OperationalIncidentView {
  id: string
  buildingId: string
  buildingName: string
  equipmentId: string
  equipmentName: string
  zoneId: string
  startedAt: string
  endedAt: string
  severity: 'low' | 'medium' | 'high' | 'critical'
  anomalyScore: number
  summary: string
}

export interface McpToolCall {
  id: string
  name: string
  purpose: string
  arguments: Record<string, unknown>
  resultSummary: string
  status: 'complete' | 'failed'
}

export interface RagRetrieval {
  id: string
  source: string
  section: string
  content: string
  score: number
}

export interface InvestigationAssessmentView {
  likelyIssue: string
  confidence: number
  explanation: string
  telemetryFindings: string[]
  maintenanceFindings: string[]
  occupantImpact: string[]
  recommendedNextStep: string
}

export interface ProposedWorkOrder {
  title: string
  buildingId: string
  equipmentId: string
  description: string
  priority: 'low' | 'medium' | 'high'
  status: 'waiting' | 'approved' | 'rejected'
  resultingId?: string
}

export type WorkOrderDecision = 'waiting' | 'approved' | 'rejected'
export type DetectionOutcome = 'not_run' | 'anomaly_detected' | 'normal'

export interface LabRunState {
  config: ExperimentConfig
  stages: PipelineStage[]
  selectedStageId: PipelineStageId
  activeTab: InspectorTab
  workOrderDecision: WorkOrderDecision
  detectionOutcome: DetectionOutcome
  isRunning: boolean
}

export type InspectorTab = 'overview' | 'inputs' | 'outputs' | 'visuals'

export interface OperationsView {
  incident: OperationalIncidentView
  telemetry: TelemetryPoint[]
  evidence: EvidenceItem[]
  assessment: InvestigationAssessmentView
  complaintsCount: number
  investigationStatus: 'investigating' | 'assessment_ready' | 'approved' | 'rejected'
  proposedWorkOrder: ProposedWorkOrder
}
