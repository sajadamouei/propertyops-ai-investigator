import { Play, RotateCcw, SkipForward } from 'lucide-react'
import type { ExperimentConfig, ExperimentScenario, FaultType } from '../../types'

interface ExperimentControlsProps {
  config: ExperimentConfig
  isRunning: boolean
  onChange: (config: ExperimentConfig) => void
  onReset: () => void
  onNext: () => void
  onFullRun: () => void
}

export function ExperimentControls({ config, isRunning, onChange, onReset, onNext, onFullRun }: ExperimentControlsProps) {
  const setField = <K extends keyof ExperimentConfig>(key: K, value: ExperimentConfig[K]) => onChange({ ...config, [key]: value })
  const setFault = <K extends keyof ExperimentConfig['customFault']>(key: K, value: ExperimentConfig['customFault'][K]) => onChange({ ...config, customFault: { ...config.customFault, [key]: value } })

  return (
    <section className="lab-controls panel-dark">
      <div className="controls-heading">
        <div><span className="lab-eyebrow">Experiment setup</span><h2>Pipeline controls</h2></div>
        <div className="run-actions">
          <button className="button button-ghost-dark" onClick={onReset} disabled={isRunning}><RotateCcw size={15} /> Reset</button>
          <button className="button button-outline-dark" onClick={onNext} disabled={isRunning}><SkipForward size={15} /> Run next step</button>
          <button className="button button-lime" onClick={onFullRun} disabled={isRunning}><Play size={15} fill="currentColor" /> Run full pipeline</button>
        </div>
      </div>
      <div className="control-grid">
        <label className="control-field control-wide"><span>Scenario</span><select value={config.scenario} onChange={(event) => setField('scenario', event.target.value as ExperimentScenario)} disabled={isRunning}><option value="fault">Heating Valve Fault</option><option value="normal">Normal Operation</option><option value="custom">Custom Fault</option></select></label>
        <label className="control-field"><span>Days</span><input type="number" min="1" max="60" value={config.days} onChange={(event) => setField('days', Number(event.target.value))} disabled={isRunning} /></label>
        <label className="control-field"><span>Random seed</span><input type="number" min="0" value={config.randomSeed} onChange={(event) => setField('randomSeed', Number(event.target.value))} disabled={isRunning} /></label>
        <div className="scenario-summary"><span className={`scenario-dot scenario-${config.scenario}`} /><div><strong>{config.scenario === 'fault' ? 'Known demo incident' : config.scenario === 'normal' ? 'Baseline validation' : 'User-defined injection'}</strong><small>{config.scenario === 'normal' ? 'No incident expected' : 'Incident path expected'}</small></div></div>
      </div>

      {config.scenario === 'custom' && (
        <div className="custom-fault" aria-label="Custom fault specification">
          <div className="custom-fault-title"><strong>Fault injection</strong><span>Applied after base telemetry generation</span></div>
          <div className="fault-grid">
            <label className="control-field"><span>Sensor</span><select value={config.customFault.sensorId} onChange={(event) => setFault('sensorId', event.target.value)} disabled={isRunning}><option>AHU01-POWER</option><option>AHU01-HEAT-VALVE</option><option>AHU01-SUPPLY-TEMP</option><option>AHU01-FAN</option><option>ZONE03-TEMP</option></select></label>
            <label className="control-field"><span>Start</span><input type="datetime-local" value={config.customFault.start} onChange={(event) => setFault('start', event.target.value)} disabled={isRunning} /></label>
            <label className="control-field"><span>End</span><input type="datetime-local" value={config.customFault.end} onChange={(event) => setFault('end', event.target.value)} disabled={isRunning} /></label>
            <label className="control-field"><span>Fault type</span><select value={config.customFault.type} onChange={(event) => setFault('type', event.target.value as FaultType)} disabled={isRunning}><option value="spike">Spike</option><option value="multiplier">Multiplier</option><option value="offset">Offset</option><option value="stuck">Stuck</option><option value="missing">Missing</option></select></label>
            <label className="control-field"><span>Value / parameter</span><input type="number" step="0.1" value={config.customFault.value} onChange={(event) => setFault('value', Number(event.target.value))} disabled={isRunning || config.customFault.type === 'missing'} /></label>
          </div>
        </div>
      )}
    </section>
  )
}
