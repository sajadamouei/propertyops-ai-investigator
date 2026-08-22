import { FlaskConical, PauseCircle } from 'lucide-react'
import { useMemo } from 'react'
import { ExperimentControls } from '../components/lab/ExperimentControls'
import { Pipeline } from '../components/lab/Pipeline'
import { StageInspector } from '../components/lab/StageInspector'
import { useDemoRun } from '../state/DemoRunContext'

export function LabPage() {
  const {
    runState,
    backendResults,
    setExperimentConfig,
    resetRun,
    runNextStep,
    runFullPipeline,
    selectStage,
    setInspectorTab,
    decideWorkOrder,
  } = useDemoRun()
  const selectedStage = useMemo(
    () => runState.stages.find((stage) => stage.id === runState.selectedStageId) ?? runState.stages[0],
    [runState.stages, runState.selectedStageId],
  )
  const completed = runState.stages.filter((stage) => stage.status === 'complete').length

  return (
    <div className="lab-page">
      <div className="lab-page-inner">
        <header className="lab-page-header">
          <div><span className="lab-title-icon"><FlaskConical size={18} /></span><div><span className="lab-eyebrow">Engineering workspace</span><h1>Investigation Lab</h1><p>Step through the pipeline using deterministic backend outputs and staged AI simulation.</p></div></div>
          <div className="run-summary"><span>{completed} / 9 complete</span><div><i style={{ width: `${(completed / 9) * 100}%` }} /></div>{runState.stages.some((stage) => stage.status === 'waiting') && <small><PauseCircle size={13} /> Waiting for approval</small>}</div>
        </header>
        <ExperimentControls
          config={runState.config}
          isRunning={runState.isRunning}
          onChange={setExperimentConfig}
          onReset={resetRun}
          onNext={runNextStep}
          onFullRun={runFullPipeline}
        />
        <Pipeline stages={runState.stages} selectedId={runState.selectedStageId} onSelect={selectStage} />
        <StageInspector
          stage={selectedStage}
          activeTab={runState.activeTab}
          onTabChange={setInspectorTab}
          approvalDecision={runState.workOrderDecision}
          onApprovalDecision={decideWorkOrder}
          backendResults={backendResults}
          stageError={runState.stageErrors[selectedStage.id]}
        />
        <footer className="lab-footer"><span className={`scenario-dot scenario-${runState.config.scenario}`} /> Stages 1–4 and 6 use the FastAPI backend · Stages 5 and 7–9 remain simulated</footer>
      </div>
    </div>
  )
}
