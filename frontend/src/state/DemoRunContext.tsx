import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { operationsView as knownIncidentView, stageDefinitions } from '../mocks/mockData'
import type {
  ExperimentConfig,
  InspectorTab,
  LabRunState,
  OperationsView,
  PipelineStage,
  PipelineStageId,
  WorkOrderDecision,
} from '../types'

const WORK_ORDER_ID = 'WO-DEMO-1042'

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

function initialState(config = defaultExperimentConfig): LabRunState {
  return {
    config,
    stages: freshStages(),
    selectedStageId: 'generate',
    activeTab: 'overview',
    workOrderDecision: 'waiting',
    detectionOutcome: 'not_run',
    isRunning: false,
  }
}

interface DemoRunContextValue {
  runState: LabRunState
  operationsView: OperationsView | null
  setExperimentConfig: (config: ExperimentConfig) => void
  resetRun: () => void
  runNextStep: () => void
  runFullPipeline: () => void
  selectStage: (stageId: PipelineStageId) => void
  setInspectorTab: (tab: InspectorTab) => void
  decideWorkOrder: (decision: Exclude<WorkOrderDecision, 'waiting'>) => void
}

const DemoRunContext = createContext<DemoRunContextValue | null>(null)

export function DemoRunProvider({ children }: { children: ReactNode }) {
  const [runState, setRunState] = useState<LabRunState>(() => initialState())
  const timers = useRef<number[]>([])

  const clearTimers = useCallback(() => {
    timers.current.forEach(window.clearTimeout)
    timers.current = []
  }, [])

  useEffect(() => clearTimers, [clearTimers])

  const replaceRun = useCallback((config: ExperimentConfig) => {
    clearTimers()
    setRunState(initialState(config))
  }, [clearTimers])

  const setExperimentConfig = useCallback((config: ExperimentConfig) => {
    replaceRun(config)
  }, [replaceRun])

  const resetRun = useCallback(() => {
    replaceRun(defaultExperimentConfig)
  }, [replaceRun])

  const selectStage = useCallback((selectedStageId: PipelineStageId) => {
    setRunState((current) => ({ ...current, selectedStageId, activeTab: 'overview' }))
  }, [])

  const setInspectorTab = useCallback((activeTab: InspectorTab) => {
    setRunState((current) => ({ ...current, activeTab }))
  }, [])

  const runNextStep = useCallback(() => {
    if (runState.isRunning) return

    const nextIndex = runState.stages.findIndex((stage) => stage.status === 'ready')
    if (nextIndex < 0) return

    const nextStage = runState.stages[nextIndex]
    setRunState((current) => ({
      ...current,
      isRunning: true,
      selectedStageId: nextStage.id,
      stages: current.stages.map((stage, index) => index === nextIndex ? { ...stage, status: 'running' } : stage),
    }))

    const timer = window.setTimeout(() => {
      setRunState((current) => {
        if (current.config.scenario === 'normal' && nextStage.id === 'detection') {
          return {
            ...current,
            isRunning: false,
            detectionOutcome: 'normal',
            stages: current.stages.map((stage, index) => index < 3 ? { ...stage, status: 'complete' } : { ...stage, status: 'skipped' }),
          }
        }

        return {
          ...current,
          isRunning: false,
          detectionOutcome: nextStage.id === 'detection' ? 'anomaly_detected' : current.detectionOutcome,
          stages: current.stages.map((stage, index) => {
            if (index === nextIndex) return { ...stage, status: nextStage.id === 'approval' ? 'waiting' : 'complete' }
            if (index === nextIndex + 1 && nextStage.id !== 'approval') return { ...stage, status: 'ready' }
            return stage
          }),
        }
      })
    }, 480)
    timers.current.push(timer)
  }, [runState])

  const runFullPipeline = useCallback(() => {
    clearTimers()
    const baseStages = freshStages()
    const isNormal = runState.config.scenario === 'normal'
    const terminalIndex = isNormal ? 2 : 7

    setRunState((current) => ({
      ...initialState(current.config),
      isRunning: true,
    }))

    baseStages.forEach((stage, index) => {
      if (index > terminalIndex) return

      const startTimer = window.setTimeout(() => {
        setRunState((current) => ({
          ...current,
          selectedStageId: stage.id,
          stages: current.stages.map((item, itemIndex) => itemIndex === index ? { ...item, status: 'running' } : item),
        }))
      }, index * 180)

      const finishTimer = window.setTimeout(() => {
        setRunState((current) => ({
          ...current,
          isRunning: index === terminalIndex ? false : current.isRunning,
          detectionOutcome: index === 2 ? (isNormal ? 'normal' : 'anomaly_detected') : current.detectionOutcome,
          stages: current.stages.map((item, itemIndex) => {
            if (isNormal && itemIndex > 2) return { ...item, status: 'skipped' }
            if (itemIndex === index) return { ...item, status: index === 7 ? 'waiting' : 'complete' }
            if (itemIndex === index + 1 && index < terminalIndex) return { ...item, status: 'ready' }
            return item
          }),
        }))
      }, index * 180 + 150)

      timers.current.push(startTimer, finishTimer)
    })
  }, [clearTimers, runState.config])

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
    const incidentBuilt = runState.stages.find((stage) => stage.id === 'incident')?.status === 'complete'
    if (!incidentBuilt || runState.detectionOutcome !== 'anomaly_detected') return null

    const assessmentComplete = runState.stages.find((stage) => stage.id === 'assessment')?.status === 'complete'
    const investigationStatus = runState.workOrderDecision === 'approved'
      ? 'approved'
      : runState.workOrderDecision === 'rejected'
        ? 'rejected'
        : assessmentComplete
          ? 'assessment_ready'
          : 'investigating'

    return {
      ...knownIncidentView,
      investigationStatus,
      proposedWorkOrder: {
        ...knownIncidentView.proposedWorkOrder,
        status: runState.workOrderDecision,
        resultingId: runState.workOrderDecision === 'approved' ? WORK_ORDER_ID : undefined,
      },
    }
  }, [runState])

  const value = useMemo<DemoRunContextValue>(() => ({
    runState,
    operationsView,
    setExperimentConfig,
    resetRun,
    runNextStep,
    runFullPipeline,
    selectStage,
    setInspectorTab,
    decideWorkOrder,
  }), [runState, operationsView, setExperimentConfig, resetRun, runNextStep, runFullPipeline, selectStage, setInspectorTab, decideWorkOrder])

  return <DemoRunContext.Provider value={value}>{children}</DemoRunContext.Provider>
}

export function useDemoRun(): DemoRunContextValue {
  const context = useContext(DemoRunContext)
  if (!context) throw new Error('useDemoRun must be used within DemoRunProvider')
  return context
}
