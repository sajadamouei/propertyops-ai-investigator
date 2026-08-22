import { apiRequest } from './client'

export type ApiScenario = 'heating_valve_fault' | 'normal_operation' | 'custom_fault'
export type ApiFaultType = 'spike' | 'multiplier' | 'offset' | 'stuck' | 'missing'
export type ApiPipelineStep =
  | 'generate_data'
  | 'feature_engineering'
  | 'anomaly_detection'
  | 'build_incident'
  | 'ai_investigation'
  | 'rag'
  | 'assessment'
  | 'human_approval'
  | 'work_order'

export interface ApiFaultSpec {
  sensor_id: string
  fault_type: ApiFaultType
  start: string
  end: string
  value?: number
}

export interface ResetRunRequest {
  scenario: ApiScenario
  days: number
  seed: number
  faults?: ApiFaultSpec[]
}

export interface ApiExperimentConfig {
  scenario: ApiScenario
  days: number
  seed: number
  start_at: string
  faults: ApiFaultSpec[]
}

export interface RunManifest {
  run_id: string
  config: ApiExperimentConfig
  status: 'ready' | 'running' | 'waiting' | 'complete' | 'failed'
  current_step: ApiPipelineStep | null
  completed_steps: ApiPipelineStep[]
  created_at: string
  updated_at: string
}

export interface RunResponse {
  manifest: RunManifest
}

export interface GenerateStageResponse {
  step: 'generate_data'
  row_count: number
  sensor_ids: string[]
}

export interface FeatureStageResponse {
  step: 'feature_engineering'
  row_count: number
  columns: string[]
}

export interface DetectionStageResponse {
  step: 'anomaly_detection'
  threshold: number
  anomalous_observations: number
  event_count: number
}

export interface TelemetryEvidenceResponse {
  metric: string
  value: number
  unit: string | null
  aggregation: string
}

export interface OperationalIncidentResponse {
  id: string
  building_id: string
  equipment_id: string
  started_at: string
  ended_at: string
  severity: 'low' | 'medium' | 'high' | 'critical'
  anomaly_score: number
  summary: string
  evidence: TelemetryEvidenceResponse[]
}

export interface IncidentStageResponse {
  step: 'build_incident'
  incident: OperationalIncidentResponse | null
}

export interface RagStageRequest {
  query?: string | null
  k?: number
}

export interface RagRetrievalResult {
  chunk_id: string
  source: string
  text: string
  score: number
}

export interface RagStageResponse {
  step: 'rag'
  query: string
  retrieval_queries: string[]
  embedding_model: string
  results: RagRetrievalResult[]
}

export interface ArtifactTableResponse {
  columns: string[]
  rows: Array<Record<string, unknown>>
  total_rows: number
}

export interface DetectionSummaryResponse {
  threshold: number
  anomalous_observations: number
  event_count: number
}

export interface RealPipelineResults {
  manifest: RunManifest | null
  generation: GenerateStageResponse | null
  rawTelemetry: ArtifactTableResponse | null
  featureStage: FeatureStageResponse | null
  features: ArtifactTableResponse | null
  detectionStage: DetectionStageResponse | null
  anomalyScores: ArtifactTableResponse | null
  events: ArtifactTableResponse | null
  detectionSummary: DetectionSummaryResponse | null
  incidentStage: IncidentStageResponse | null
  ragStage: RagStageResponse | null
}

const post = <T>(path: string, body?: unknown) => apiRequest<T>(path, {
  method: 'POST',
  ...(body === undefined ? {} : { body: JSON.stringify(body) }),
})

const artifact = (path: string, limit = 1000) => apiRequest<ArtifactTableResponse>(`${path}?limit=${limit}`)

export const propertyOpsApi = {
  resetRun: (request: ResetRunRequest) => post<RunResponse>('/api/runs/reset', request),
  getCurrentRun: () => apiRequest<RunResponse>('/api/runs/current'),
  generate: () => post<GenerateStageResponse>('/api/pipeline/generate'),
  features: () => post<FeatureStageResponse>('/api/pipeline/features'),
  detect: () => post<DetectionStageResponse>('/api/pipeline/detect'),
  incident: () => post<IncidentStageResponse>('/api/pipeline/incident'),
  rag: (request: RagStageRequest) => post<RagStageResponse>('/api/pipeline/rag', request),
  rawTelemetry: (limit?: number) => artifact('/api/artifacts/raw-telemetry', limit),
  featureArtifact: (limit?: number) => artifact('/api/artifacts/features', limit),
  anomalyScores: (limit?: number) => artifact('/api/artifacts/anomaly-scores', limit),
  events: (limit?: number) => artifact('/api/artifacts/events', limit),
  detectionSummary: () => apiRequest<DetectionSummaryResponse>('/api/artifacts/detection'),
}
