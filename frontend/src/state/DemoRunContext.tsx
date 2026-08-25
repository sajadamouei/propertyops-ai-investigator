import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { propertyOpsApi, type RealPipelineResults, type ResetRunRequest, type RunRecoveryResponse } from '../api/propertyOpsApi'
import { operationsView as knownIncidentView, stageDefinitions } from '../mocks/mockData'
import type {
  ExperimentConfig,
  InspectorTab,
  LabRunState,
  OperationsView,
  PipelineStage,
  PipelineStageId,
  TelemetryPoint,
  WorkOrderDecision,
} from '../types'

const FOUNDATION_REAL_STAGE_IDS: PipelineStageId[] = ['generate', 'features', 'detection', 'incident']
const NO_INCIDENT_STAGE_IDS: PipelineStageId[] = ['incident', 'investigation', 'rag', 'assessment', 'approval', 'work-order']

export const defaultExperimentConfig: ExperimentConfig = {
  scenario: 'fault',
  days: 14,
  randomSeed: 42,
  customFault: {
    sensorId: 'AHU01-HEAT-VALVE',
    start: '2026-01-15T01:00',
    end: '2026-01-15T05:00',
    type: 'stuck',
    value: 94,
  },
}

function freshStages(): PipelineStage[] {
  return stageDefinitions.map((stage) => ({ ...stage }))
}

function emptyBackendResults(): RealPipelineResults {
  return {
    manifest: null,
    generation: null,
    rawTelemetry: null,
    featureStage: null,
    features: null,
    detectionStage: null,
    anomalyScores: null,
    events: null,
    detectionSummary: null,
    incidentStage: null,
    ragStage: null,
    investigation: null,
    mcpTrace: [],
    assessment: null,
    approvalRequest: null,
    approval: null,
    workOrder: null,
  }
}

function initialState(config = defaultExperimentConfig): LabRunState {
  return {
    config,
    stages: freshStages(),
    selectedStageId: 'generate',
    activeTab: 'overview',
    workOrderDecision: 'waiting',
    detectionOutcome: 'not_run',
    isRunning: false,
    stageErrors: {},
  }
}

const STAGE_TO_API_STEP = {
  generate: 'generate_data',
  features: 'feature_engineering',
  detection: 'anomaly_detection',
  incident: 'build_incident',
  investigation: 'ai_investigation',
  rag: 'rag',
  assessment: 'assessment',
  approval: 'human_approval',
  'work-order': 'work_order',
} as const satisfies Record<PipelineStageId, string>

function inputDateTime(value: string): string {
  return value.slice(0, 16)
}

function recoveredConfig(snapshot: RunRecoveryResponse): ExperimentConfig {
  const backendConfig = snapshot.manifest.config
  const scenario = backendConfig.scenario === 'heating_valve_fault'
    ? 'fault'
    : backendConfig.scenario === 'normal_operation'
      ? 'normal'
      : 'custom'
  const fault = backendConfig.faults[0]

  return {
    scenario,
    days: backendConfig.days,
    randomSeed: backendConfig.seed,
    customFault: fault
      ? {
          sensorId: fault.sensor_id,
          start: inputDateTime(fault.start),
          end: inputDateTime(fault.end),
          type: fault.fault_type,
          value: fault.value ?? defaultExperimentConfig.customFault.value,
        }
      : { ...defaultExperimentConfig.customFault },
  }
}

function recoveredResults(snapshot: RunRecoveryResponse): RealPipelineResults {
  return {
    manifest: snapshot.manifest,
    generation: snapshot.generation,
    rawTelemetry: snapshot.raw_telemetry,
    featureStage: snapshot.feature_stage,
    features: snapshot.features,
    detectionStage: snapshot.detection_stage,
    anomalyScores: snapshot.anomaly_scores,
    events: snapshot.events,
    detectionSummary: snapshot.detection_summary,
    incidentStage: snapshot.incident_stage,
    ragStage: snapshot.rag ? { ...snapshot.rag, step: 'rag' } : null,
    investigation: snapshot.investigation,
    mcpTrace: snapshot.mcp_trace,
    assessment: snapshot.assessment,
    approvalRequest: snapshot.approval_request,
    approval: snapshot.approval,
    workOrder: snapshot.work_order,
  }
}

function recoveredRunState(snapshot: RunRecoveryResponse, config: ExperimentConfig): LabRunState {
  const completedSteps = new Set(snapshot.manifest.completed_steps)
  const noIncident = completedSteps.has('build_incident') && snapshot.incident_stage?.incident === null
  const stages: PipelineStage[] = freshStages().map((stage) => ({
    ...stage,
    status: completedSteps.has(STAGE_TO_API_STEP[stage.id]) ? 'complete' as const : 'not_started' as const,
  }))

  if (noIncident) {
    stages.forEach((stage) => {
      if (NO_INCIDENT_STAGE_IDS.includes(stage.id)) stage.status = 'skipped'
    })
  } else if (snapshot.approval && !snapshot.approval.approved) {
    const workOrder = stages.find((stage) => stage.id === 'work-order')
    if (workOrder) workOrder.status = 'skipped'
  }

  const currentStage = stages.find(
    (stage) => STAGE_TO_API_STEP[stage.id] === snapshot.manifest.current_step,
  )
  if (currentStage) {
    currentStage.status = snapshot.manifest.status === 'waiting'
      ? 'waiting'
      : snapshot.manifest.status === 'failed'
        ? 'failed'
        : 'running'
  } else if (snapshot.manifest.status === 'ready' && !noIncident) {
    const nextStage = stages.find((stage) => stage.status === 'not_started')
    if (nextStage) nextStage.status = 'ready'
  }

  const selectedStageId = snapshot.manifest.status === 'waiting' || snapshot.approval
    ? 'approval'
    : noIncident
      ? 'incident'
      : currentStage?.id ?? [...stages].reverse().find((stage) => stage.status === 'complete')?.id ?? 'generate'

  const detectionOutcome = snapshot.incident_stage
    ? snapshot.incident_stage.incident
      ? 'anomaly_detected'
      : 'normal'
    : snapshot.detection_stage
      ? snapshot.detection_stage.event_count > 0
        ? 'anomaly_detected'
        : 'normal'
      : 'not_run'

  return {
    config,
    stages,
    selectedStageId,
    activeTab: 'overview',
    workOrderDecision: snapshot.approval
      ? snapshot.approval.approved ? 'approved' : 'rejected'
      : 'waiting',
    detectionOutcome,
    isRunning: snapshot.manifest.status === 'running',
    stageErrors: {},
  }
}

function resetRequest(config: ExperimentConfig): ResetRunRequest {
  const scenario = config.scenario === 'fault'
    ? 'heating_valve_fault'
    : config.scenario === 'normal'
      ? 'normal_operation'
      : 'custom_fault'

  if (config.scenario !== 'custom') {
    return { scenario, days: config.days, seed: config.randomSeed }
  }

  const fault = config.customFault
  return {
    scenario,
    days: config.days,
    seed: config.randomSeed,
    faults: [{
      sensor_id: fault.sensorId,
      fault_type: fault.type,
      start: fault.start,
      end: fault.end,
      ...(fault.type === 'missing' ? {} : { value: fault.value }),
    }],
  }
}

function configurationKey(config: ExperimentConfig): string {
  return JSON.stringify(resetRequest(config))
}

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : 'The pipeline stage failed unexpectedly.'
}

function toNumber(value: unknown): number {
  return typeof value === 'number' ? value : Number(value)
}

function toBoolean(value: unknown): boolean {
  return value === true || String(value).toLowerCase() === 'true'
}

function telemetryLabel(timestamp: string): string {
  const match = timestamp.match(/(\d{2}:\d{2})/)
  return match?.[1] ?? timestamp
}

function scoredTelemetry(rows: Array<Record<string, unknown>>): TelemetryPoint[] {
  return rows.flatMap((row) => {
    const timestamp = String(row.timestamp ?? '')
    const powerKw = toNumber(row.power_kw)
    const heatingValvePct = toNumber(row.heating_valve_pct)
    const supplyAirTempC = toNumber(row.supply_air_temp_c)
    const fanStatus = toNumber(row.fan_status)
    const anomalyScore = toNumber(row.anomaly_score)
    if (!timestamp || [powerKw, heatingValvePct, supplyAirTempC, fanStatus, anomalyScore].some(Number.isNaN)) return []
    return [{
      timestamp,
      label: telemetryLabel(timestamp),
      powerKw,
      heatingValvePct,
      supplyAirTempC,
      fanStatus,
      anomalyScore,
      isAnomaly: toBoolean(row.is_anomaly),
    }]
  })
}

function incidentTelemetry(rows: Array<Record<string, unknown>>, startedAt: string, endedAt: string): TelemetryPoint[] {
  const points = scoredTelemetry(rows)
  const start = new Date(startedAt).getTime() - 2 * 60 * 60 * 1000
  const end = new Date(endedAt).getTime() + 2 * 60 * 60 * 1000
  const window = points.filter((point) => {
    const timestamp = new Date(point.timestamp).getTime()
    return timestamp >= start && timestamp <= end
  })
  return window.length ? window : points.slice(0, 24)
}

interface DemoRunContextValue {
  runState: LabRunState
  backendResults: RealPipelineResults
  operationsView: OperationsView | null
  setExperimentConfig: (config: ExperimentConfig) => void
  resetRun: () => Promise<void>
  runNextStep: () => Promise<void>
  runFullPipeline: () => Promise<void>
  selectStage: (stageId: PipelineStageId) => void
  setInspectorTab: (tab: InspectorTab) => void
  decideWorkOrder: (decision: Exclude<WorkOrderDecision, 'waiting'>) => Promise<void>
}

const DemoRunContext = createContext<DemoRunContextValue | null>(null)

export function DemoRunProvider({ children }: { children: ReactNode }) {
  const [runState, setRunState] = useState<LabRunState>(() => initialState())
  const [backendResults, setBackendResults] = useState<RealPipelineResults>(() => emptyBackendResults())
  const [recoveryStatus, setRecoveryStatus] = useState<'loading' | 'ready' | 'error'>('loading')
  const [recoveryError, setRecoveryError] = useState<string | null>(null)
  const recoveryRequest = useRef<Promise<RunRecoveryResponse | null> | null>(null)
  const backendConfigKey = useRef<string | null>(null)
  const approvalRequestInFlight = useRef(false)

  useEffect(() => {
    let active = true
    recoveryRequest.current ??= propertyOpsApi.recoverCurrentRun()

    void recoveryRequest.current
      .then((snapshot) => {
        if (!active) return
        if (snapshot) {
          const config = recoveredConfig(snapshot)
          backendConfigKey.current = configurationKey(config)
          setBackendResults(recoveredResults(snapshot))
          setRunState(recoveredRunState(snapshot, config))
        }
        setRecoveryStatus('ready')
      })
      .catch((error) => {
        if (!active) return
        setRecoveryError(errorMessage(error))
        setRecoveryStatus('error')
      })

    return () => {
      active = false
    }
  }, [])

  const replaceRun = useCallback((config: ExperimentConfig) => {
    backendConfigKey.current = null
    setBackendResults(emptyBackendResults())
    setRunState(initialState(config))
  }, [])

  const setExperimentConfig = useCallback((config: ExperimentConfig) => {
    replaceRun(config)
  }, [replaceRun])

  const initializeBackend = useCallback(async (config: ExperimentConfig, force = false) => {
    const key = configurationKey(config)
    if (!force && backendConfigKey.current === key) return
    const response = await propertyOpsApi.resetRun(resetRequest(config))
    backendConfigKey.current = key
    setBackendResults({ ...emptyBackendResults(), manifest: response.manifest })
  }, [])

  const resetRun = useCallback(async () => {
    if (runState.isRunning) return
    const config = runState.config
    backendConfigKey.current = null
    setBackendResults(emptyBackendResults())
    setRunState({ ...initialState(config), isRunning: true })
    try {
      await initializeBackend(config, true)
      setRunState(initialState(config))
    } catch (error) {
      setRunState({
        ...initialState(config),
        selectedStageId: 'generate',
        stageErrors: { generate: errorMessage(error) },
      })
    }
  }, [initializeBackend, runState.config, runState.isRunning])

  const selectStage = useCallback((selectedStageId: PipelineStageId) => {
    setRunState((current) => ({ ...current, selectedStageId, activeTab: 'overview' }))
  }, [])

  const setInspectorTab = useCallback((activeTab: InspectorTab) => {
    setRunState((current) => ({ ...current, activeTab }))
  }, [])

  const startStage = useCallback((stageId: PipelineStageId) => {
    setRunState((current) => ({
      ...current,
      isRunning: true,
      selectedStageId: stageId,
      stageErrors: { ...current.stageErrors, [stageId]: undefined },
      stages: current.stages.map((stage) => stage.id === stageId ? { ...stage, status: 'running' } : stage),
    }))
  }, [])

  const completeStage = useCallback((stageId: PipelineStageId) => {
    setRunState((current) => {
      const stageIndex = current.stages.findIndex((stage) => stage.id === stageId)
      return {
        ...current,
        stages: current.stages.map((stage, index) => {
          if (stage.id === stageId) return { ...stage, status: 'complete' }
          if (index === stageIndex + 1 && stage.status === 'not_started') return { ...stage, status: 'ready' }
          return stage
        }),
      }
    })
  }, [])

  const failStage = useCallback((stageId: PipelineStageId, error: unknown) => {
    setRunState((current) => ({
      ...current,
      isRunning: false,
      selectedStageId: stageId,
      stageErrors: { ...current.stageErrors, [stageId]: errorMessage(error) },
      stages: current.stages.map((stage) => stage.id === stageId ? { ...stage, status: 'failed' } : stage),
    }))
  }, [])

  const executeRealStage = useCallback(async (stageId: PipelineStageId, config: ExperimentConfig): Promise<boolean> => {
    await initializeBackend(config)

    if (stageId === 'generate') {
      const generation = await propertyOpsApi.generate()
      const rawTelemetry = await propertyOpsApi.rawTelemetry()
      setBackendResults((current) => ({ ...current, generation, rawTelemetry }))
      completeStage(stageId)
      return true
    }

    if (stageId === 'features') {
      const featureStage = await propertyOpsApi.features()
      const features = await propertyOpsApi.featureArtifact()
      setBackendResults((current) => ({ ...current, featureStage, features }))
      completeStage(stageId)
      return true
    }

    if (stageId === 'detection') {
      const detectionStage = await propertyOpsApi.detect()
      const [anomalyScores, events, detectionSummary] = await Promise.all([
        propertyOpsApi.anomalyScores(),
        propertyOpsApi.events(),
        propertyOpsApi.detectionSummary(),
      ])
      setBackendResults((current) => ({ ...current, detectionStage, anomalyScores, events, detectionSummary }))
      setRunState((current) => ({
        ...current,
        detectionOutcome: detectionStage.event_count > 0 ? 'anomaly_detected' : 'normal',
      }))
      completeStage(stageId)
      return true
    }

    if (stageId === 'incident') {
      const incidentStage = await propertyOpsApi.incident()
      setBackendResults((current) => ({ ...current, incidentStage }))
      if (incidentStage.incident) {
        setRunState((current) => ({ ...current, detectionOutcome: 'anomaly_detected' }))
        completeStage(stageId)
        return true
      }

      setRunState((current) => ({
        ...current,
        detectionOutcome: 'normal',
        stages: current.stages.map((stage) => (
          NO_INCIDENT_STAGE_IDS.includes(stage.id)
            ? { ...stage, status: 'skipped' }
            : stage
        )),
      }))
      return false
    }

    return true
  }, [completeStage, initializeBackend])

  const executeWorkflowStart = useCallback(async () => {
    const response = await propertyOpsApi.workflowStart()
    setBackendResults((current) => ({
      ...current,
      manifest: response.manifest,
      investigation: response.investigation,
      mcpTrace: response.mcp_trace,
      ragStage: { ...response.rag, step: 'rag' },
      assessment: response.assessment,
      approvalRequest: response.approval_request,
      approval: null,
      workOrder: null,
    }))
    setRunState((current) => ({
      ...current,
      selectedStageId: 'approval',
      activeTab: 'overview',
      workOrderDecision: 'waiting',
      stages: current.stages.map((stage) => {
        if (['investigation', 'rag', 'assessment'].includes(stage.id)) return { ...stage, status: 'complete' }
        if (stage.id === 'approval') return { ...stage, status: 'waiting' }
        if (stage.id === 'work-order') return { ...stage, status: 'not_started' }
        return stage
      }),
    }))
  }, [])

  const runNextStep = useCallback(async () => {
    if (runState.isRunning) return
    const nextStage = runState.stages.find((stage) => stage.status === 'ready')
    if (!nextStage) return

    startStage(nextStage.id)
    try {
      if (FOUNDATION_REAL_STAGE_IDS.includes(nextStage.id)) {
        await executeRealStage(nextStage.id, runState.config)
      } else if (nextStage.id === 'investigation') {
        await executeWorkflowStart()
      }
      setRunState((current) => ({ ...current, isRunning: false }))
    } catch (error) {
      failStage(nextStage.id, error)
    }
  }, [executeRealStage, executeWorkflowStart, failStage, runState.config, runState.isRunning, runState.stages, startStage])

  const runFullPipeline = useCallback(async () => {
    if (runState.isRunning) return
    const config = runState.config
    backendConfigKey.current = null
    setBackendResults(emptyBackendResults())
    setRunState({ ...initialState(config), isRunning: true })

    let activeStage: PipelineStageId = 'generate'
    try {
      await initializeBackend(config, true)
      for (const stageId of FOUNDATION_REAL_STAGE_IDS) {
        activeStage = stageId
        startStage(stageId)
        const shouldContinue = await executeRealStage(stageId, config)
        if (!shouldContinue) {
          setRunState((current) => ({ ...current, isRunning: false }))
          return
        }
      }

      activeStage = 'investigation'
      startStage(activeStage)
      await executeWorkflowStart()
      setRunState((current) => ({ ...current, isRunning: false }))
    } catch (error) {
      failStage(activeStage, error)
    }
  }, [executeRealStage, executeWorkflowStart, failStage, initializeBackend, runState.config, runState.isRunning, startStage])

  const decideWorkOrder = useCallback(async (
    decision: Exclude<WorkOrderDecision, 'waiting'>,
  ) => {
    const approvalIsWaiting = runState.stages.find(
      (stage) => stage.id === 'approval',
    )?.status === 'waiting'

    if (
      !approvalIsWaiting ||
      runState.workOrderDecision !== 'waiting' ||
      runState.isRunning ||
      approvalRequestInFlight.current
    ) {
      return
    }

    approvalRequestInFlight.current = true

    setRunState((current) => ({
      ...current,
      isRunning: true,
      selectedStageId: 'approval',
      stageErrors: {
        ...current.stageErrors,
        approval: undefined,
      },
    }))

    try {
      const response = await propertyOpsApi.workflowDecision({
        approved: decision === 'approved',
        rationale: decision === 'approved'
          ? 'Approved by operator in PropertyOps UI.'
          : 'Rejected by operator in PropertyOps UI.',
      })

      const backendDecision: WorkOrderDecision = (
        response.approval.approved
          ? 'approved'
          : 'rejected'
      )

      setBackendResults((current) => ({
        ...current,
        manifest: response.manifest,
        approval: response.approval,
        workOrder: response.work_order,
      }))

      setRunState((current) => ({
        ...current,
        isRunning: false,
        workOrderDecision: backendDecision,
        stages: current.stages.map((stage) => {
          if (stage.id === 'approval') {
            return {
              ...stage,
              status: 'complete',
            }
          }

          if (stage.id === 'work-order') {
            return {
              ...stage,
              status: (
                backendDecision === 'approved'
                  ? 'complete'
                  : 'skipped'
              ),
            }
          }

          return stage
        }),
      }))
    } catch (error) {
      setRunState((current) => ({
        ...current,
        isRunning: false,
        selectedStageId: 'approval',
        stageErrors: {
          ...current.stageErrors,
          approval: errorMessage(error),
        },
      }))
    } finally {
      approvalRequestInFlight.current = false
    }
  }, [
    runState.isRunning,
    runState.stages,
    runState.workOrderDecision,
  ])

  const operationsView = useMemo<OperationsView | null>(() => {
    const incident = backendResults.incidentStage?.incident
    const incidentBuilt = runState.stages.find((stage) => stage.id === 'incident')?.status === 'complete'
    if (!incidentBuilt || !incident) return null

    const investigation = backendResults.investigation
    const assessment = backendResults.assessment
    const investigationStatus = backendResults.approval?.approved
      ? 'approved'
      : backendResults.approval
        ? 'rejected'
        : assessment
          ? 'assessment_ready'
          : 'investigating'

    const telemetry = backendResults.anomalyScores
      ? incidentTelemetry(backendResults.anomalyScores.rows, incident.started_at, incident.ended_at)
      : []
    const evidence = investigation ? [
      ...investigation.telemetry_findings.map((detail, index) => ({ id: `telemetry-${index}`, category: 'telemetry' as const, title: `Telemetry finding ${index + 1}`, detail })),
      ...investigation.maintenance_findings.map((detail, index) => ({ id: `maintenance-${index}`, category: 'maintenance' as const, title: `Maintenance finding ${index + 1}`, detail })),
      ...investigation.occupant_impact.map((detail, index) => ({ id: `tenant-${index}`, category: 'tenant' as const, title: `Occupant impact ${index + 1}`, detail })),
    ] : []

    return {
      ...knownIncidentView,
      incident: {
        ...knownIncidentView.incident,
        id: incident.id,
        buildingId: incident.building_id,
        equipmentId: incident.equipment_id,
        startedAt: incident.started_at,
        endedAt: incident.ended_at,
        severity: incident.severity,
        anomalyScore: incident.anomaly_score,
        summary: incident.summary,
      },
      telemetry,
      evidence,
      complaintsCount: investigation?.occupant_impact.length ?? 0,
      assessment: {
        likelyIssue: assessment?.likely_issue ?? '',
        confidence: assessment?.confidence ?? 0,
        explanation: investigation?.summary ?? '',
        telemetryFindings: assessment?.telemetry_findings ?? [],
        maintenanceFindings: assessment?.maintenance_findings ?? [],
        occupantImpact: assessment?.occupant_impact ?? [],
        recommendedNextStep: assessment?.recommended_next_step ?? '',
      },
      detectionThreshold: backendResults.detectionSummary?.threshold,
      investigationStatus,
      proposedWorkOrder: {
        ...knownIncidentView.proposedWorkOrder,
        buildingId: incident.building_id,
        equipmentId: incident.equipment_id,
        description: assessment?.recommended_next_step ?? backendResults.approvalRequest?.recommended_next_step ?? '',
        status: backendResults.approval ? (backendResults.approval.approved ? 'approved' : 'rejected') : 'waiting',
        resultingId: backendResults.workOrder?.work_order.id,
      },
    }
  }, [backendResults, runState])

  const value = useMemo<DemoRunContextValue>(() => ({
    runState,
    backendResults,
    operationsView,
    setExperimentConfig,
    resetRun,
    runNextStep,
    runFullPipeline,
    selectStage,
    setInspectorTab,
    decideWorkOrder,
  }), [runState, backendResults, operationsView, setExperimentConfig, resetRun, runNextStep, runFullPipeline, selectStage, setInspectorTab, decideWorkOrder])

  if (recoveryStatus === 'loading') {
    return <div className="app-recovery" role="status">Restoring current run…</div>
  }

  if (recoveryStatus === 'error') {
    return <div className="app-recovery app-recovery-error" role="alert">Unable to restore the current run. {recoveryError}</div>
  }

  return <DemoRunContext.Provider value={value}>{children}</DemoRunContext.Provider>
}

export function useDemoRun(): DemoRunContextValue {
  const context = useContext(DemoRunContext)
  if (!context) throw new Error('useDemoRun must be used within DemoRunProvider')
  return context
}
