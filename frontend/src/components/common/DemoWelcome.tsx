import { ArrowRight } from 'lucide-react'
import { Fragment } from 'react'
import { Link } from 'react-router-dom'
import { engineeringChallenges, investigationWorkflow, recommendedRun, technologyGroups } from '../../content/demoGuide'
import { DemoDialog } from './DemoDialog'

interface DemoWelcomeProps {
  onDismiss: () => void
  onOpenGuide: () => void
}

export function DemoWelcome({ onDismiss, onOpenGuide }: DemoWelcomeProps) {
  return (
    <DemoDialog
      variant="welcome"
      eyebrow="PropertyOps AI Investigator"
      title="From fragmented building data to evidence-based maintenance decisions"
      onDismiss={onDismiss}
      footer={
        <>
          <div className="demo-first-run">
            <span className="eyebrow">Recommended first run</span>
            <strong>{recommendedRun.name}</strong>
            <small>{recommendedRun.action}</small>
          </div>
          <div className="demo-welcome-actions">
            <Link className="button button-primary" to="/lab" onClick={onDismiss}>
              Start in Lab <ArrowRight size={16} aria-hidden="true" />
            </Link>
            <button type="button" className="button button-secondary" onClick={onDismiss}>Explore on my own</button>
            <button type="button" className="demo-text-action" onClick={onOpenGuide}>How does the demo work?</button>
          </div>
        </>
      }
    >
      <section className="demo-section">
        <h3>The real-world challenge</h3>
        <p>Buildings generate sensor readings, equipment records, maintenance history, tenant complaints, and technical documentation across separate systems. When something goes wrong, operators have to piece together those signals and consult technical guidance before deciding what to do. That makes investigations slow, repetitive, and hard to scale.</p>
      </section>

      <section className="demo-section">
        <h3>The PropertyOps approach</h3>
        <p>PropertyOps uses machine learning to flag unusual HVAC patterns, an AI agent to gather evidence, and retrieval-augmented generation (RAG) to find troubleshooting guidance. It combines those inputs into an assessment and recommended action, then pauses so a person decides whether to change any records.</p>
        <ol className="demo-flow" aria-label="Investigation workflow" role="list">
          {investigationWorkflow.map(({ action }, index) => (
            <li key={action}>
              {index > 0 && <ArrowRight size={13} aria-hidden="true" />}
              <span>{action}</span>
            </li>
          ))}
        </ol>
      </section>

      <section className="demo-section">
        <h3>What you can explore</h3>
        <ol className="demo-welcome-steps" role="list">
          {investigationWorkflow.map(({ label, detail }, index) => (
            <li key={label}>
              <span className="demo-step-number" aria-hidden="true">{index + 1}</span>
              <div><strong>{label}</strong><p>{detail}</p></div>
            </li>
          ))}
        </ol>
      </section>

      <section className="demo-section">
        <h3>Engineering challenges explored</h3>
        <dl className="demo-detail-list demo-challenges">
          {engineeringChallenges.map(({ title, detail }) => (
            <div key={title}><dt>{title}</dt><dd>{detail}</dd></div>
          ))}
        </dl>
      </section>

      <section className="demo-section">
        <h3>Built with</h3>
        <dl className="demo-technology">
          {technologyGroups.map(({ title, items }) => (
            <Fragment key={title}>
              <dt>{title}</dt>
              <dd>{items.map((item) => <span key={item}>{item}</span>)}</dd>
            </Fragment>
          ))}
        </dl>
      </section>
      <p className="demo-note">This portfolio demo uses simulated building and operational data.</p>
    </DemoDialog>
  )
}
