import { AlertTriangle, ArrowRight, CheckCircle2, ClipboardList, Gauge, MessageSquareText, ShieldCheck, Sparkles, Wrench } from 'lucide-react'
import { SeverityBadge } from '../components/common/Badges'
import { ApprovalCard } from '../components/operations/ApprovalCard'
import { EvidenceGroup } from '../components/operations/EvidenceGroup'
import { TelemetryChart } from '../components/operations/TelemetryChart'
import { useDemoRun } from '../state/DemoRunContext'

export function OperationsPage() {
  const { runState, operationsView, decideWorkOrder } = useDemoRun()

  if (!operationsView) {
    return <OperationsNormalState />
  }

  const groups = {
    telemetry: operationsView.evidence.filter((item) => item.category === 'telemetry'),
    maintenance: operationsView.evidence.filter((item) => item.category === 'maintenance'),
    tenant: operationsView.evidence.filter((item) => item.category === 'tenant'),
  }
  const assessmentReady = operationsView.investigationStatus !== 'investigating'
  const evidenceReady = runState.stages.find((stage) => stage.id === 'investigation')?.status === 'complete'
  const approvalStageStatus = runState.stages.find((stage) => stage.id === 'approval')?.status
  const approvalAvailable = approvalStageStatus === 'waiting' || runState.workOrderDecision !== 'waiting'
  const investigationCopy = {
    investigating: { label: 'Investigation in progress', detail: 'Collecting operational evidence' },
    assessment_ready: { label: 'Assessment ready', detail: 'Awaiting operator decision' },
    approved: { label: 'Work order approved', detail: operationsView.proposedWorkOrder.resultingId ?? 'Action approved' },
    rejected: { label: 'Action rejected', detail: 'No work order created' },
  }[operationsView.investigationStatus]

  return (
    <div className="page operations-page">
      <section className="incident-header">
        <div className="incident-header-main">
          <div className="incident-kicker"><span className="pulse-ring"><AlertTriangle size={14} /></span> Current incident</div>
          <div className="incident-title-row">
            <div>
              <h1>Heating delivery anomaly</h1>
              <p>{operationsView.incident.buildingName} · {operationsView.incident.buildingId}</p>
            </div>
            <SeverityBadge severity={operationsView.incident.severity} />
          </div>
          <div className="incident-meta">
            <div><span>Equipment</span><strong>{operationsView.incident.equipmentId}</strong><small>{operationsView.incident.equipmentName}</small></div>
            <div><span>Incident window</span><strong>15 Jan 2026 · 01:00–05:00</strong><small>5 consecutive hours</small></div>
            <div><span>Investigation</span><strong className="status-inline"><CheckCircle2 size={15} /> {investigationCopy.label}</strong><small>{investigationCopy.detail}</small></div>
            <div><span>Incident ID</span><strong>{operationsView.incident.id}</strong><small>{operationsView.incident.zoneId} affected</small></div>
          </div>
        </div>
      </section>

      <section className="summary-grid" aria-label="Incident summary">
        <article className="stat-card"><div className="stat-icon score"><Sparkles size={18} /></div><div><span>Anomaly score</span><strong>{operationsView.incident.anomalyScore.toFixed(4)}</strong><small>Above 0.6069 threshold</small></div></article>
        <article className="stat-card"><div className="stat-icon complaints"><MessageSquareText size={18} /></div><div><span>Tenant complaints</span><strong>{evidenceReady ? operationsView.complaintsCount : '—'}</strong><small>{evidenceReady ? `Cold comfort · ${operationsView.incident.zoneId}` : 'Investigation pending'}</small></div></article>
        <article className="stat-card"><div className="stat-icon state"><Wrench size={18} /></div><div><span>Equipment status</span><strong>{operationsView.investigationStatus === 'approved' ? 'Inspection approved' : operationsView.investigationStatus === 'rejected' ? 'Action declined' : 'Needs inspection'}</strong><small>AHU is currently operational</small></div></article>
      </section>

      <div className="operations-main-grid">
        <TelemetryChart data={operationsView.telemetry} />
        <aside className="panel assessment-card">
          {assessmentReady ? (
            <>
              <div className="panel-heading"><div><span className="eyebrow">AI assessment</span><h2>Likely control fault</h2></div><span className="confidence-ring">{Math.round(operationsView.assessment.confidence * 100)}%<small>confidence</small></span></div>
              <div className="assessment-highlight"><span>Likely issue</span><strong>{operationsView.assessment.likelyIssue}</strong></div>
              <p>{operationsView.assessment.explanation}</p>
              <div className="assessment-note"><AlertTriangle size={15} /><span>This is an evidence-based hypothesis, not a confirmed root cause.</span></div>
            </>
          ) : (
            <div className="assessment-pending">
              <span className="pending-icon"><Gauge size={21} /></span>
              <span className="eyebrow">AI assessment</span>
              <h2>Investigation in progress</h2>
              <p>The incident is active. The pipeline is still gathering evidence before it can recommend an operational action.</p>
            </div>
          )}
        </aside>
      </div>

      <section className="panel evidence-panel">
        <div className="panel-heading"><div><span className="eyebrow">Investigation record</span><h2>{evidenceReady ? 'Evidence reviewed' : 'Evidence collection pending'}</h2></div>{evidenceReady && <span className="record-count">7 findings</span>}</div>
        {evidenceReady ? (
          <div className="evidence-grid">
            <EvidenceGroup title="Telemetry" subtitle="3 findings" items={groups.telemetry} />
            <EvidenceGroup title="Maintenance history" subtitle="1 relevant record" items={groups.maintenance} />
            <EvidenceGroup title="Tenant impact" subtitle="3 complaints" items={groups.tenant} />
          </div>
        ) : (
          <div className="evidence-pending"><Gauge size={18} /><span>Advance the AI Investigation stage to collect maintenance and tenant-impact evidence.</span></div>
        )}
      </section>

      {assessmentReady ? (
        <>
          <section className="recommendation-card">
            <div className="recommendation-number">01</div>
            <div><span className="eyebrow">Recommended next action</span><h2>Inspect the actuator before replacing components</h2><p>{operationsView.assessment.recommendedNextStep}</p></div>
            <ArrowRight size={24} />
          </section>
          {approvalAvailable ? (
            <ApprovalCard workOrder={operationsView.proposedWorkOrder} onDecision={decideWorkOrder} />
          ) : (
            <section className="approval-card approval-unavailable">
              <div className="approval-icon"><ClipboardList size={21} /></div>
              <div className="approval-main"><span className="eyebrow">Human approval</span><h2>Approval stage is ready</h2><p>Advance the pipeline to Human Approval in the Lab before recording an operator decision.</p></div>
            </section>
          )}
        </>
      ) : (
        <section className="recommendation-card recommendation-pending">
          <div className="recommendation-number">—</div>
          <div><span className="eyebrow">Recommended next action</span><h2>Pending investigation</h2><p>Complete the evidence and assessment stages before preparing an operational action.</p></div>
        </section>
      )}
      <footer className="page-footer"><ClipboardList size={14} /> Prototype view · Data and decisions remain in the browser</footer>
    </div>
  )
}

function OperationsNormalState() {
  const { runState } = useDemoRun()
  const normalConfirmed = runState.detectionOutcome === 'normal'
  const anomalyInProgress = runState.detectionOutcome === 'anomaly_detected'
  const headerTitle = normalConfirmed ? 'No active incidents' : anomalyInProgress ? 'Incident analysis in progress' : 'No active investigation'
  const headerDescription = normalConfirmed
    ? 'Building systems operating normally'
    : anomalyInProgress
      ? 'A potential anomaly is moving through the investigation pipeline'
      : 'Run a scenario in the Lab to populate this operational view'

  return (
    <div className="page operations-page">
      <section className="incident-header normal-state-header">
        <div className="incident-header-main">
          <div className="incident-kicker"><span className="normal-ring"><CheckCircle2 size={15} /></span> Operations overview</div>
          <div className="incident-title-row">
            <div><h1>{headerTitle}</h1><p>{headerDescription}</p></div>
            <span className="badge normal-badge">{normalConfirmed ? 'Systems normal' : anomalyInProgress ? 'Processing' : 'Ready'}</span>
          </div>
          <div className="incident-meta">
            <div><span>Building</span><strong>BLDG-001</strong><small>Property operations</small></div>
            <div><span>Latest pipeline run</span><strong>{runState.isRunning ? 'In progress' : normalConfirmed ? 'Completed' : anomalyInProgress ? 'In progress' : 'Not run'}</strong><small>{runState.config.scenario === 'normal' ? 'Normal Operation' : runState.config.scenario === 'fault' ? 'Heating Valve Fault' : 'Custom Fault'}</small></div>
            <div><span>Anomaly detection</span><strong className="status-inline"><CheckCircle2 size={15} /> {normalConfirmed ? 'No anomaly detected' : anomalyInProgress ? 'Anomaly detected' : 'Awaiting run'}</strong><small>{normalConfirmed ? 'Detection threshold 0.6069' : 'Pipeline status is synchronized'}</small></div>
            <div><span>Work order</span><strong>{normalConfirmed ? 'Not required' : 'None created'}</strong><small>No pending maintenance action</small></div>
          </div>
        </div>
      </section>

      <section className="summary-grid" aria-label="Building status summary">
        <article className="stat-card"><div className="stat-icon normal"><ShieldCheck size={18} /></div><div><span>System health</span><strong>{normalConfirmed ? 'Normal' : anomalyInProgress ? 'Under review' : 'No active alert'}</strong><small>BLDG-001</small></div></article>
        <article className="stat-card"><div className="stat-icon score"><Sparkles size={18} /></div><div><span>Detection run</span><strong>{normalConfirmed ? 'Complete' : runState.isRunning ? 'Running' : 'Not complete'}</strong><small>{normalConfirmed ? 'No incident created' : 'Use the Investigation Lab'}</small></div></article>
        <article className="stat-card"><div className="stat-icon state"><Wrench size={18} /></div><div><span>Required action</span><strong>{normalConfirmed ? 'None' : anomalyInProgress ? 'Await results' : 'No action'}</strong><small>{normalConfirmed ? 'No work order required' : 'No operator decision pending'}</small></div></article>
      </section>

      <section className="panel normal-state-panel">
        <span className="normal-state-icon"><CheckCircle2 size={26} /></span>
        <div>
          <span className="eyebrow">Latest operational result</span>
          <h2>{normalConfirmed ? 'All monitored signals are within the expected operating pattern' : anomalyInProgress ? 'The pipeline is building the operational incident' : 'Operations is ready for the next investigation run'}</h2>
          <p>{normalConfirmed ? 'Generate Data, Feature Engineering, and Anomaly Detection completed successfully. No incident was created, downstream investigation stages were skipped, and no work order is required.' : anomalyInProgress ? 'An anomaly was detected. This view will update automatically when the incident and assessment stages complete.' : 'Select and run a scenario in the Lab. Results and approval decisions will stay synchronized here during this browser session.'}</p>
        </div>
      </section>
      <footer className="page-footer"><ClipboardList size={14} /> Prototype view · Data and decisions remain in the browser</footer>
    </div>
  )
}
