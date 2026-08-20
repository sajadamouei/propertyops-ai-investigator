import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { propertyOpsApi, type RealPipelineResults, type ResetRunRequest } from '../api/propertyOpsApi'
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

const WORK_ORDER_ID = 'WO-DEMO-1042'
const REAL_STAGE_IDS: PipelineStageId[] = ['generate', 'features', 'detection', 'incident']

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
  decideWorkOrder: (decision: Exclude<WorkOrderDecision, 'waiting'>) => void
}

const DemoRunContext = createContext<DemoRunContextValue | null>(null)

export function DemoRunProvider({ children }: { children: ReactNode }) {
  const [runState, setRunState] = useState<LabRunState>(() => initialState())
  const [backendResults, setBackendResults] = useState<RealPipelineResults>(() => emptyBackendResults())
  const backendConfigKey = useRef<string | null>(null)
  const timers = useRef<number[]>([])

  const clearTimers = useCallback(() => {
    timers.current.forEach(window.clearTimeout)
    timers.current = []
  }, [])

  useEffect(() => clearTimers, [clearTimers])

  const replaceRun = useCallback((config: ExperimentConfig) => {
    clearTimers()
    backendConfigKey.current = null
    setBackendResults(emptyBackendResults())
    setRunState(initialState(config))
  }, [clearTimers])

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
    clearTimers()
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
  }, [clearTimers, initializeBackend, runState.config, runState.isRunning])

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
          stage.id === 'incident' || !REAL_STAGE_IDS.includes(stage.id)
            ? { ...stage, status: 'skipped' }
            : stage
        )),
      }))
      return false
    }

    return true
  }, [completeStage, initializeBackend])

  const executeMockStage = useCallback((stageId: PipelineStageId) => new Promise<void>((resolve) => {
    const timer = window.setTimeout(() => {
      if (stageId === 'approval') {
        setRunState((current) => ({
          ...current,
          stages: current.stages.map((stage) => stage.id === stageId ? { ...stage, status: 'waiting' } : stage),
        }))
      } else {
        completeStage(stageId)
      }
      resolve()
    }, 180)
    timers.current.push(timer)
  }), [completeStage])

  const runNextStep = useCallback(async () => {
    if (runState.isRunning) return
    const nextStage = runState.stages.find((stage) => stage.status === 'ready')
    if (!nextStage) return

    startStage(nextStage.id)
    try {
      if (REAL_STAGE_IDS.includes(nextStage.id)) {
        await executeRealStage(nextStage.id, runState.config)
      } else {
        await executeMockStage(nextStage.id)
      }
      setRunState((current) => ({ ...current, isRunning: false }))
    } catch (error) {
      failStage(nextStage.id, error)
    }
  }, [executeMockStage, executeRealStage, failStage, runState.config, runState.isRunning, runState.stages, startStage])

  const runFullPipeline = useCallback(async () => {
    if (runState.isRunning) return
    const config = runState.config
    clearTimers()
    backendConfigKey.current = null
    setBackendResults(emptyBackendResults())
    setRunState({ ...initialState(config), isRunning: true })

    let activeStage: PipelineStageId = 'generate'
    try {
      await initializeBackend(config, true)
      for (const stageId of REAL_STAGE_IDS) {
        activeStage = stageId
        startStage(stageId)
        const shouldContinue = await executeRealStage(stageId, config)
        if (!shouldContinue) {
          setRunState((current) => ({ ...current, isRunning: false }))
          return
        }
      }

      for (const stageId of ['investigation', 'rag', 'assessment', 'approval'] as PipelineStageId[]) {
        activeStage = stageId
        startStage(stageId)
        await executeMockStage(stageId)
      }
      setRunState((current) => ({ ...current, isRunning: false }))
    } catch (error) {
      failStage(activeStage, error)
    }
  }, [clearTimers, executeMockStage, executeRealStage, failStage, initializeBackend, runState.config, runState.isRunning, startStage])

  const decideWorkOrder = useCallback((decision: Exclude<WorkOrderDecision, 'waiting'>) => {
    setRunState((current) => {
      const approvalIsWaiting = current.stages.find((stage) => stage.id === 'approval')?.status === 'waiting'
      if (!approvalIsWaiting || current.workOrderDecision !== 'waiting') return current

      return {
        ...current,
        workOrderDecision: decision,
        stages: current.stages.map((stage) => {
          if (stage.id === 'approval') return { ...stage, status: 'complete' }
          if (stage.id === 'work-order') return { ...stage, status: decision === 'approved' ? 'complete' : 'skipped' }
          return stage
        }),
      }
    })
  }, [])

  const operationsView = useMemo<OperationsView | null>(() => {
    const incident = backendResults.incidentStage?.incident
    const incidentBuilt = runState.stages.find((stage) => stage.id === 'incident')?.status === 'complete'
    if (!incidentBuilt || !incident) return null

    const assessmentComplete = runState.stages.find((stage) => stage.id === 'assessment')?.status === 'complete'
    const investigationStatus = runState.workOrderDecision === 'approved'
      ? 'approved'
      : runState.workOrderDecision === 'rejected'
        ? 'rejected'
        : assessmentComplete
          ? 'assessment_ready'
          : 'investigating'

    const telemetry = backendResults.anomalyScores
      ? incidentTelemetry(backendResults.anomalyScores.rows, incident.started_at, incident.ended_at)
      : []

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
      detectionThreshold: backendResults.detectionSummary?.threshold,
      investigationStatus,
      proposedWorkOrder: {
        ...knownIncidentView.proposedWorkOrder,
        buildingId: incident.building_id,
        equipmentId: incident.equipment_id,
        status: runState.workOrderDecision,
        resultingId: runState.workOrderDecision === 'approved' ? WORK_ORDER_ID : undefined,
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

  return <DemoRunContext.Provider value={value}>{children}</DemoRunContext.Provider>
}

export function useDemoRun(): DemoRunContextValue {
  const context = useContext(DemoRunContext)
  if (!context) throw new Error('useDemoRun must be used within DemoRunProvider')
  return context
}
