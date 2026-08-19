import { AlertCircle, Box, CheckCircle2, Database, FileSearch, Gauge, Info, Search, Wrench } from 'lucide-react'
import { Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { mcpCalls, operationsView, ragRetrievals, rawTelemetryRows, telemetry } from '../../mocks/mockData'
import type { ExperimentConfig, InspectorTab, PipelineStage, PipelineStageId } from '../../types'
import { StageStatusBadge } from '../common/Badges'

interface StageInspectorProps {
  stage: PipelineStage
  config: ExperimentConfig
  activeTab: InspectorTab
  onTabChange: (tab: InspectorTab) => void
  approvalDecision: 'waiting' | 'approved' | 'rejected'
  onApprovalDecision: (decision: 'approved' | 'rejected') => void
}

const tabs: InspectorTab[] = ['overview', 'inputs', 'outputs', 'visuals']

const stageFacts: Record<PipelineStageId, Array<{ label: string; value: string }>> = {
  generate: [{ label: 'Records', value: '1,680' }, { label: 'Sensors', value: '5' }, { label: 'Cadence', value: '1 hour' }],
  features: [{ label: 'Rows', value: '336' }, { label: 'Features', value: '6' }, { label: 'Null values', value: '0' }],
  detection: [{ label: 'Model', value: 'Isolation Forest' }, { label: 'Threshold', value: '0.6069' }, { label: 'Events', value: '1' }],
  incident: [{ label: 'Incident', value: 'INC-…-AHU01' }, { label: 'Duration', value: '5 hours' }, { label: 'Severity', value: 'High' }],
  investigation: [{ label: 'Tool calls', value: '4' }, { label: 'Sources', value: '3' }, { label: 'Write calls', value: '0' }],
  rag: [{ label: 'Query', value: '1' }, { label: 'Retrieved', value: '3 chunks' }, { label: 'Top score', value: '0.93' }],
  assessment: [{ label: 'Confidence', value: '85%' }, { label: 'Evidence items', value: '7' }, { label: 'Schema', value: 'Valid' }],
  approval: [{ label: 'Decision', value: 'Required' }, { label: 'Priority', value: 'High' }, { label: 'Side effects', value: 'Blocked' }],
  'work-order': [{ label: 'Work order', value: 'WO-DEMO-1042' }, { label: 'Status', value: 'Open' }, { label: 'Target', value: 'AHU-001' }],
}

export function StageInspector({ stage, config, activeTab, onTabChange, approvalDecision, onApprovalDecision }: StageInspectorProps) {
  return (
    <section className="inspector panel-dark">
      <header className="inspector-header">
        <div><span className="lab-eyebrow">Stage inspector</span><div className="inspector-title"><h2>{stage.label}</h2><StageStatusBadge status={stage.status} /></div><p>{stage.description}</p></div>
        <span className="inspector-stage-id">{stage.id}</span>
      </header>
      <div className="inspector-tabs" role="tablist">
        {tabs.map((tab) => <button key={tab} role="tab" aria-selected={activeTab === tab} className={activeTab === tab ? 'active' : ''} onClick={() => onTabChange(tab)}>{tab}</button>)}
      </div>
      <div className="inspector-body" role="tabpanel">
        {activeTab === 'overview' && <Overview stage={stage} approvalDecision={approvalDecision} onApprovalDecision={onApprovalDecision} />}
        {activeTab === 'inputs' && <Inputs stageId={stage.id} config={config} approvalDecision={approvalDecision} />}
        {activeTab === 'outputs' && <Outputs stageId={stage.id} approvalDecision={approvalDecision} />}
        {activeTab === 'visuals' && <Visuals stageId={stage.id} />}
      </div>
    </section>
  )
}

function Overview({ stage, approvalDecision, onApprovalDecision }: { stage: PipelineStage; approvalDecision: 'waiting' | 'approved' | 'rejected'; onApprovalDecision: (decision: 'approved' | 'rejected') => void }) {
  if (stage.id === 'approval') {
    return (
      <div className="approval-inspector">
        <div className="approval-inspector-copy"><span className="warning-icon"><Wrench size={20} /></span><div><h3>Inspect AHU-001 heating valve controls</h3><p>Verify actuator response, mechanical linkage, calibration, and overnight control schedule before replacing any components.</p><div className="mini-meta"><span>BLDG-001</span><span>AHU-001</span><span>High priority</span></div></div></div>
        <div className="approval-inspector-actions">
          {approvalDecision !== 'waiting'
            ? <div className={`lab-decision decision-${approvalDecision}`}><CheckCircle2 size={17} /> Decision: {approvalDecision}</div>
            : stage.status === 'waiting'
              ? <><button className="button button-lime" onClick={() => onApprovalDecision('approved')}>Approve in demo</button><button className="button button-ghost-dark" onClick={() => onApprovalDecision('rejected')}>Reject</button></>
              : <div className="lab-decision">Available when the pipeline reaches approval</div>}
        </div>
      </div>
    )
  }

  const messages: Record<PipelineStageId, string> = {
    generate: 'Produces deterministic hourly readings for AHU-001 and ZONE-003. The known fault is injected from 01:00 through 05:00 on January 15.',
    features: 'Converts long-form sensor readings to one row per timestamp, then adds occupancy context used by the detector.',
    detection: 'Fits on observations through January 14 and flags readings above the 99th-percentile training threshold.',
    incident: 'Groups consecutive anomalous hours and translates model output into an operations-friendly domain record.',
    investigation: 'The agent follows a read-only evidence trail. Sensor discovery happens before telemetry access, and operational facts come from tools.',
    rag: 'Retrieves a small set of relevant operating procedures to contextualize the observed evidence without treating documentation as proof.',
    assessment: 'Returns a typed assessment that distinguishes the likely issue from confirmed evidence and recommends a bounded next step.',
    approval: '',
    'work-order': 'A write action is available only after explicit approval. This prototype displays the resulting record but never calls the Python server.',
  }
  return (
    <div className="overview-layout">
      <div className="stage-summary"><Info size={18} /><div><h3>What this stage does</h3><p>{messages[stage.id]}</p></div></div>
      <div className="fact-grid">{stageFacts[stage.id].map((fact) => <div className="fact-card" key={fact.label}><span>{fact.label}</span><strong>{fact.value}</strong></div>)}</div>
      <div className="stage-rule"><AlertCircle size={16} /><span>{stage.id === 'work-order' ? 'Write boundary: requires an approved decision.' : stage.id === 'assessment' ? 'Output is schema-validated before presentation.' : 'All values shown here are local mock data for the frontend prototype.'}</span></div>
    </div>
  )
}

function Inputs({ stageId, config, approvalDecision }: { stageId: PipelineStageId; config: ExperimentConfig; approvalDecision: 'waiting' | 'approved' | 'rejected' }) {
  if (stageId === 'generate') return <JsonBlock title="Generation config" value={{ start: '2026-01-05T00:00:00', days: config.days, random_seed: config.randomSeed, scenario: config.scenario, fault: config.scenario === 'normal' ? null : config.scenario === 'custom' ? config.customFault : { sensor: 'multiple', start: '2026-01-15T01:00', end: '2026-01-15T05:00', profile: 'heating_valve_fault' } }} />
  if (stageId === 'features') return <TagList title="Raw columns" tags={['timestamp', 'sensor_id', 'value', 'equipment_id', 'sensor_type', 'unit']} />
  if (stageId === 'detection') return <TagList title="Model features" tags={['power_kw', 'heating_valve_pct', 'supply_air_temp_c', 'zone_temp_c', 'fan_status', 'expected_occupied']} />
  if (stageId === 'incident') return <JsonBlock title="Detected event" value={{ start: '2026-01-15T01:00:00', end: '2026-01-15T05:00:00', points: 5, max_anomaly_score: 0.6956 }} />
  if (stageId === 'investigation') return <JsonBlock title="Incident context" value={{ building_id: 'BLDG-001', equipment_id: 'AHU-001', zone_id: 'ZONE-003', incident_window: ['2026-01-15T01:00:00', '2026-01-15T05:00:00'], constraints: ['read-only investigation', 'do not invent evidence'] }} />
  if (stageId === 'rag') return <div className="query-card"><Search size={17} /><div><span>Retrieval query</span><code>AHU heating valve high command low supply temperature after-hours fan operation actuator response</code></div></div>
  if (stageId === 'assessment') return <TagList title="Evidence bundle" tags={['20 telemetry readings', '2 maintenance records', '3 tenant complaints', '3 RAG chunks']} />
  if (stageId === 'approval') return <JsonBlock title="Proposed work order" value={{ ...operationsView.proposedWorkOrder, status: approvalDecision }} />
  return <JsonBlock title="Approval token" value={{ approved_by: approvalDecision === 'approved' ? 'demo.operator' : null, decision: approvalDecision, action_authorized: approvalDecision === 'approved', proposed_action: 'create_work_order' }} />
}

function Outputs({ stageId, approvalDecision }: { stageId: PipelineStageId; approvalDecision: 'waiting' | 'approved' | 'rejected' }) {
  if (stageId === 'generate') return <DataTable title="Raw telemetry sample" columns={['sensor', 'timestamp', 'value', 'unit']} rows={rawTelemetryRows.slice(0, 8)} />
  if (stageId === 'features') return <DataTable title="Feature dataset" columns={['timestamp', 'power_kw', 'valve_pct', 'supply_c', 'occupied']} rows={telemetry.slice(1, 7).map((p) => ({ timestamp: p.label, power_kw: p.powerKw, valve_pct: p.heatingValvePct, supply_c: p.supplyAirTempC, occupied: false }))} />
  if (stageId === 'detection') return <DataTable title="Anomaly scores" columns={['timestamp', 'score', 'threshold', 'anomaly']} rows={telemetry.slice(1, 8).map((p) => ({ timestamp: p.label, score: p.anomalyScore.toFixed(4), threshold: '0.6069', anomaly: p.isAnomaly ? 'true' : 'false' }))} />
  if (stageId === 'incident') return <JsonBlock title="OperationalIncident" value={{ id: operationsView.incident.id, building_id: 'BLDG-001', equipment_id: 'AHU-001', started_at: '2026-01-15T01:00:00', ended_at: '2026-01-15T05:00:00', severity: 'high', anomaly_score: 0.6956, evidence: [{ metric: 'power_kw', value: 148.7, unit: 'kW', aggregation: 'max' }, { metric: 'heating_valve_pct', value: 95, unit: '%', aggregation: 'max' }, { metric: 'supply_air_temp_c', value: 14.4, unit: 'C', aggregation: 'min' }] }} />
  if (stageId === 'investigation') return <ToolCalls />
  if (stageId === 'rag') return <RagResults />
  if (stageId === 'assessment') return <JsonBlock title="InvestigationAssessment" value={{ likely_issue: operationsView.assessment.likelyIssue, confidence: operationsView.assessment.confidence, telemetry_findings: operationsView.assessment.telemetryFindings, maintenance_findings: operationsView.assessment.maintenanceFindings, occupant_impact: operationsView.assessment.occupantImpact, recommended_next_step: operationsView.assessment.recommendedNextStep }} />
  if (stageId === 'approval') return <JsonBlock title="Decision state" value={{ status: approvalDecision, action_authorized: approvalDecision === 'approved', recorded_locally: true }} />
  return <JsonBlock title="WorkOrder" value={{ id: approvalDecision === 'approved' ? 'WO-DEMO-1042' : null, building_id: 'BLDG-001', equipment_id: 'AHU-001', status: approvalDecision === 'approved' ? 'open' : 'not_created', note: 'Frontend mock only' }} />
}

function Visuals({ stageId }: { stageId: PipelineStageId }) {
  if (['generate', 'features', 'incident'].includes(stageId)) return <TelemetryVisual transformed={stageId === 'features'} />
  if (stageId === 'detection') return <AnomalyVisual />
  if (stageId === 'investigation') return <EvidenceCoverage />
  if (stageId === 'rag') return <RetrievalVisual />
  if (stageId === 'assessment') return <ConfidenceVisual />
  return <FlowBoundary stageId={stageId} />
}

function TelemetryVisual({ transformed }: { transformed?: boolean }) {
  return <ChartFrame title={transformed ? 'Transformed feature series' : 'AHU-001 telemetry window'} legend="Power kW and valve % share the left scale; supply air °C uses the right scale."><ResponsiveContainer width="100%" height="100%"><LineChart data={telemetry}><CartesianGrid stroke="#2d3940" vertical={false} /><XAxis dataKey="label" tick={{ fill: '#89969c', fontSize: 10 }} axisLine={false} tickLine={false} interval={1} /><YAxis yAxisId="left" tick={{ fill: '#89969c', fontSize: 10 }} axisLine={false} tickLine={false} /><YAxis yAxisId="right" orientation="right" domain={[10, 22]} tick={{ fill: '#89969c', fontSize: 10 }} axisLine={false} tickLine={false} /><Tooltip contentStyle={{ background: '#10191d', border: '1px solid #344148', borderRadius: 8 }} /><Line yAxisId="left" dataKey="powerKw" name="Power kW" stroke="#b9db75" strokeWidth={2} dot={false} /><Line yAxisId="left" dataKey="heatingValvePct" name="Valve %" stroke="#e19a65" strokeWidth={2} dot={false} /><Line yAxisId="right" dataKey="supplyAirTempC" name="Supply °C" stroke="#62b2ce" strokeWidth={2} dot={false} /></LineChart></ResponsiveContainer></ChartFrame>
}

function AnomalyVisual() {
  return <ChartFrame title="Anomaly score by timestamp" legend="Readings above 0.6069 are anomalous."><ResponsiveContainer width="100%" height="100%"><AreaChart data={telemetry}><defs><linearGradient id="scoreFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#b9db75" stopOpacity={0.35} /><stop offset="1" stopColor="#b9db75" stopOpacity={0} /></linearGradient></defs><CartesianGrid stroke="#2d3940" vertical={false} /><XAxis dataKey="label" tick={{ fill: '#89969c', fontSize: 10 }} axisLine={false} tickLine={false} interval={1} /><YAxis domain={[0.3, 0.75]} tick={{ fill: '#89969c', fontSize: 10 }} axisLine={false} tickLine={false} /><Tooltip contentStyle={{ background: '#10191d', border: '1px solid #344148', borderRadius: 8 }} /><ReferenceLine y={0.6069} stroke="#e19a65" strokeDasharray="5 4" label={{ value: 'threshold', fill: '#e19a65', fontSize: 10 }} /><Area type="monotone" dataKey="anomalyScore" stroke="#b9db75" fill="url(#scoreFill)" strokeWidth={2.5} /></AreaChart></ResponsiveContainer></ChartFrame>
}

function EvidenceCoverage() {
  const data = [{ name: 'Telemetry', items: 20 }, { name: 'Maintenance', items: 2 }, { name: 'Complaints', items: 3 }]
  return <ChartFrame title="Evidence collected by source" legend="All requested operational sources were checked."><ResponsiveContainer width="100%" height="100%"><BarChart data={data} layout="vertical" margin={{ left: 20 }}><CartesianGrid stroke="#2d3940" horizontal={false} /><XAxis type="number" tick={{ fill: '#89969c', fontSize: 10 }} axisLine={false} tickLine={false} /><YAxis type="category" dataKey="name" tick={{ fill: '#c9d2d5', fontSize: 11 }} axisLine={false} tickLine={false} width={78} /><Tooltip contentStyle={{ background: '#10191d', border: '1px solid #344148', borderRadius: 8 }} /><Bar dataKey="items" fill="#b9db75" radius={[0, 4, 4, 0]} barSize={18} /></BarChart></ResponsiveContainer></ChartFrame>
}

function RetrievalVisual() {
  return <ChartFrame title="Retrieval relevance" legend="Cosine similarity score by retrieved document chunk."><ResponsiveContainer width="100%" height="100%"><BarChart data={ragRetrievals}><CartesianGrid stroke="#2d3940" vertical={false} /><XAxis dataKey="section" tick={{ fill: '#89969c', fontSize: 9 }} axisLine={false} tickLine={false} /><YAxis domain={[0, 1]} tick={{ fill: '#89969c', fontSize: 10 }} axisLine={false} tickLine={false} /><Tooltip contentStyle={{ background: '#10191d', border: '1px solid #344148', borderRadius: 8 }} /><Bar dataKey="score" radius={[4, 4, 0, 0]}>{ragRetrievals.map((item, index) => <Cell key={item.id} fill={index === 0 ? '#b9db75' : '#618389'} />)}</Bar></BarChart></ResponsiveContainer></ChartFrame>
}

function ConfidenceVisual() {
  return <div className="confidence-visual"><div className="confidence-gauge"><Gauge size={38} /><strong>85%</strong><span>Assessment confidence</span></div><div className="confidence-breakdown"><div><span>Telemetry consistency</span><i><b style={{ width: '92%' }} /></i><strong>92%</strong></div><div><span>Maintenance corroboration</span><i><b style={{ width: '80%' }} /></i><strong>80%</strong></div><div><span>Occupant correlation</span><i><b style={{ width: '83%' }} /></i><strong>83%</strong></div></div></div>
}

function FlowBoundary({ stageId }: { stageId: PipelineStageId }) {
  return <div className="flow-boundary"><div><Box size={20} /><strong>Assessment</strong></div><span className="boundary-line"><em>explicit operator decision</em></span><div className={stageId === 'work-order' ? 'active' : ''}><Wrench size={20} /><strong>Work order</strong></div></div>
}

function ToolCalls() {
  return <div className="tool-call-list">{mcpCalls.map((call, index) => <article className="tool-call" key={call.id}><div className="tool-sequence">{index + 1}</div><div className="tool-call-main"><div className="tool-call-heading"><code>{call.name}</code><span><CheckCircle2 size={13} /> complete</span></div><p>{call.purpose}</p><div className="tool-io"><div><small>Arguments</small><pre>{JSON.stringify(call.arguments, null, 2)}</pre></div><div><small>Result</small><span>{call.resultSummary}</span></div></div></div></article>)}</div>
}

function RagResults() {
  return <div className="rag-results">{ragRetrievals.map((item, index) => <article className="rag-card" key={item.id}><div className="rag-rank">0{index + 1}</div><div><div className="rag-heading"><span><FileSearch size={14} />{item.source}</span><strong>{item.score.toFixed(2)}</strong></div><small>{item.section}</small><p>{item.content}</p></div></article>)}</div>
}

function JsonBlock({ title, value }: { title: string; value: unknown }) {
  return <div className="json-block"><div className="code-heading"><span><Database size={14} />{title}</span><small>mock payload</small></div><pre>{JSON.stringify(value, null, 2)}</pre></div>
}

function TagList({ title, tags }: { title: string; tags: string[] }) {
  return <div className="tag-list"><h3>{title}</h3><div>{tags.map((tag) => <code key={tag}>{tag}</code>)}</div></div>
}

function DataTable({ title, columns, rows }: { title: string; columns: string[]; rows: Array<Record<string, unknown>> }) {
  return <div className="data-table-wrap"><h3>{title}</h3><div className="table-scroll"><table><thead><tr>{columns.map((column) => <th key={column}>{column}</th>)}</tr></thead><tbody>{rows.map((row, index) => <tr key={index}>{columns.map((column) => <td key={column}>{String(row[column])}</td>)}</tr>)}</tbody></table></div></div>
}

function ChartFrame({ title, legend, children }: { title: string; legend: string; children: React.ReactNode }) {
  return <div className="lab-chart-frame"><div><h3>{title}</h3><p>{legend}</p></div><div className="lab-chart">{children}</div></div>
}
