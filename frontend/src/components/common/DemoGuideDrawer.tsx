import { ArrowRight, ExternalLink } from 'lucide-react'
import type { RefObject } from 'react'
import { Link } from 'react-router-dom'
import { demoScenarios, investigationWorkflow, projectLinks, recommendedRun, simulationSources, telemetryStage } from '../../content/demoGuide'
import { DemoDialog } from './DemoDialog'

interface DemoGuideDrawerProps {
  onDismiss: () => void
  returnFocusRef: RefObject<HTMLButtonElement | null>
}

export function DemoGuideDrawer({ onDismiss, returnFocusRef }: DemoGuideDrawerProps) {
  return (
    <DemoDialog
      variant="drawer"
      title="Demo guide"
      onDismiss={onDismiss}
      returnFocusRef={returnFocusRef}
      footer={
        <div className="demo-guide-links">
          {projectLinks.map(({ label, href }) => (
            <a className="demo-text-action" key={href} href={href} target="_blank" rel="noopener noreferrer">
              {label} <ExternalLink size={14} aria-hidden="true" />
            </a>
          ))}
        </div>
      }
    >
      <section className="demo-section">
        <h3>About the demo</h3>
        <p>PropertyOps demonstrates how anomaly detection and AI agents can combine building telemetry, maintenance history, tenant complaints, and technical guidance into one evidence-based investigation workflow.</p>
      </section>

      <section className="demo-section">
        <h3>Try the demo</h3>
        <div className="demo-first-run">
          <span className="eyebrow">Recommended first run</span>
          <strong>{recommendedRun.name}</strong>
          <small>{recommendedRun.days} days · Seed {recommendedRun.seed}</small>
        </div>
        <ol className="demo-run-instructions">
          <li>Open Lab.</li>
          <li>Keep {recommendedRun.name} selected.</li>
          <li>Click <strong>{recommendedRun.action}</strong>.</li>
          <li>Inspect the pipeline and AI assessment.</li>
          <li>Open Operations.</li>
          <li>Review and approve or reject the proposed demo work order.</li>
        </ol>
        <Link className="button button-primary" to="/lab" onClick={onDismiss}>
          Open Lab <ArrowRight size={16} aria-hidden="true" />
        </Link>
      </section>

      <section className="demo-section">
        <h3>What happens behind the scenes</h3>
        <ol className="demo-guide-workflow" role="list">
          {[telemetryStage, ...investigationWorkflow].map(({ title, detail }, index) => (
            <li key={title}>
              <span className="demo-step-number" aria-hidden="true">{String(index + 1).padStart(2, '0')}</span>
              <div><strong>{title}</strong><p>{detail}</p></div>
            </li>
          ))}
        </ol>
        <p className="demo-note">LangGraph saves the investigation state so it can resume after your decision.</p>
      </section>

      <section className="demo-section">
        <h3>Understand the scenarios</h3>
        <dl className="demo-detail-list demo-scenario-list">
          {Object.entries(demoScenarios).map(([scenario, { name, description }]) => (
            <div key={scenario}>
              <dt>{name}{scenario === recommendedRun.scenario && <span className="demo-recommended">Recommended</span>}</dt>
              <dd>{description}</dd>
            </div>
          ))}
        </dl>
      </section>

      <section className="demo-section">
        <h3>Lab vs Operations</h3>
        <dl className="demo-detail-list">
          <div>
            <dt>Lab · Experiment and inspect</dt>
            <dd>Choose scenarios, configure faults, run the pipeline, and inspect individual stages.</dd>
          </div>
          <div>
            <dt>Operations · Review and decide</dt>
            <dd>Review the incident, evidence, AI assessment, recommendation, and approval state.</dd>
          </div>
        </dl>
      </section>

      <section className="demo-section">
        <h3>What is simulated</h3>
        <dl className="demo-detail-list">
          {simulationSources.map(({ title, detail }) => (
            <div key={title}><dt>{title}</dt><dd>{detail}</dd></div>
          ))}
        </dl>
        <p className="demo-note">Nothing in the demo controls physical equipment or creates a real maintenance request.</p>
      </section>
    </DemoDialog>
  )
}
