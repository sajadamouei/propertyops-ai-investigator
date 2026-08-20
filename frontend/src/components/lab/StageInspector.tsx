import { AlertCircle, Box, CheckCircle2, Database, FileSearch, Gauge, Info, Search, Wrench } from 'lucide-react'
import { Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { RealPipelineResults } from '../../api/propertyOpsApi'
import { mcpCalls, operationsView, ragRetrievals } from '../../mocks/mockData'
import type { InspectorTab, PipelineStage, PipelineStageId } from '../../types'
import { StageStatusBadge } from '../common/Badges'

interface StageInspectorProps {
  stage: PipelineStage
  activeTab: InspectorTab
  onTabChange: (tab: InspectorTab) => void
  approvalDecision: 'waiting' | 'approved' | 'rejected'
  onApprovalDecision: (decision: 'approved' | 'rejected') => void
  backendResults: RealPipelineResults
  stageError?: string
}

const tabs: InspectorTab[] = ['overview', 'inputs', 'outputs', 'visuals']

const stageFacts: Partial<Record<PipelineStageId, Array<{ label: string; value: string }>>> = {
  investigation: [{ label: 'Tool calls', value: '4' }, { label: 'Sources', value: '3' }, { label: 'Write calls', value: '0' }],
  rag: [{ label: 'Query', value: '1' }, { label: 'Retrieved', value: '3 chunks' }, { label: 'Top score', value: '0.93' }],
  assessment: [{ label: 'Confidence', value: '85%' }, { label: 'Evidence items', value: '7' }, { label: 'Schema', value: 'Valid' }],
  approval: [{ label: 'Decision', value: 'Required' }, { label: 'Priority', value: 'High' }, { label: 'Side effects', value: 'Blocked' }],
  'work-order': [{ label: 'Work order', value: 'WO-DEMO-1042' }, { label: 'Status', value: 'Open' }, { label: 'Target', value: 'AHU-001' }],
}

const realStageIds: PipelineStageId[] = ['generate', 'features', 'detection', 'incident']

export function StageInspector({ stage, activeTab, onTabChange, approvalDecision, onApprovalDecision, backendResults, stageError }: StageInspectorProps) {
  const isRealStage = realStageIds.includes(stage.id)
  return (
    <section className="inspector panel-dark">
      <header className="inspector-header">
        <div><span className="lab-eyebrow">Stage inspector</span><div className="inspector-title"><h2>{stage.label}</h2><StageStatusBadge status={stage.status} /></div><p>{stage.description}</p></div>
        <div className="inspector-source"><span className={`source-badge ${isRealStage ? 'source-real' : 'source-mock'}`}>{isRealStage ? 'REAL BACKEND' : 'MOCK - NOT YET CONNECTED'}</span><span className="inspector-stage-id">{stage.id}</span></div>
      </header>
      <div className="inspector-tabs" role="tablist">
        {tabs.map((tab) => <button key={tab} role="tab" aria-selected={activeTab === tab} className={activeTab === tab ? 'active' : ''} onClick={() => onTabChange(tab)}>{tab}</button>)}
      </div>
      <div className="inspector-body" role="tabpanel">
        {stageError && <div className="stage-error" role="alert"><AlertCircle size={16} /><span>{stageError}</span></div>}
        {isRealStage
          ? <RealStageContent stageId={stage.id} activeTab={activeTab} results={backendResults} />
          : <>
              {activeTab === 'overview' && <Overview stage={stage} approvalDecision={approvalDecision} onApprovalDecision={onApprovalDecision} />}
              {activeTab === 'inputs' && <Inputs stageId={stage.id} approvalDecision={approvalDecision} />}
              {activeTab === 'outputs' && <Outputs stageId={stage.id} approvalDecision={approvalDecision} />}
              {activeTab === 'visuals' && <Visuals stageId={stage.id} />}
            </>}
      </div>
    </section>
  )
}

function RealStageContent({ stageId, activeTab, results }: { stageId: PipelineStageId; activeTab: InspectorTab; results: RealPipelineResults }) {
  if (activeTab === 'overview') return <RealOverview stageId={stageId} results={results} />
  if (activeTab === 'inputs') return <RealInputs stageId={stageId} results={results} />
  if (activeTab === 'outputs') return <RealOutputs stageId={stageId} results={results} />
  return <RealVisuals stageId={stageId} results={results} />
}

function RealOverview({ stageId, results }: { stageId: PipelineStageId; results: RealPipelineResults }) {
  const config = results.manifest?.config
  if (stageId === 'generate') {
    if (!config) return <AwaitingBackend />
    const facts = [
      { label: 'Scenario', value: config.scenario },
      { label: 'Days', value: String(config.days) },
      { label: 'Seed', value: String(config.seed) },
      { label: 'Rows', value: results.generation ? results.generation.row_count.toLocaleString() : 'Not generated' },
      { label: 'Sensors', value: results.generation ? String(results.generation.sensor_ids.length) : 'Not generated' },
    ]
    return <RealOverviewLayout summary="Creates deterministic sensor readings from the backend experiment configuration." facts={facts} detail={results.generation?.sensor_ids.join(', ')} />
  }
  if (stageId === 'features') {
    if (!results.featureStage) return <AwaitingBackend />
    return <RealOverviewLayout summary="Pivots the raw readings and adds the operating-context features used by detection." facts={[{ label: 'Rows', value: results.featureStage.row_count.toLocaleString() }, { label: 'Columns', value: String(results.featureStage.columns.length) }]} detail={results.featureStage.columns.join(', ')} />
  }
  if (stageId === 'detection') {
    if (!results.detectionStage) return <AwaitingBackend />
    return <RealOverviewLayout summary="Scores the real feature table and groups consecutive anomalous observations into events." facts={[{ label: 'Threshold', value: results.detectionStage.threshold.toFixed(4) }, { label: 'Anomalous observations', value: String(results.detectionStage.anomalous_observations) }, { label: 'Events', value: String(results.detectionStage.event_count) }]} />
  }
  const incident = results.incidentStage?.incident
  if (!results.incidentStage) return <AwaitingBackend />
  if (!incident) return <div className="real-empty"><CheckCircle2 size={22} /><h3>No operational incident</h3><p>The backend completed incident building and returned no incident. Downstream incident-dependent stages were skipped.</p></div>
  return <RealOverviewLayout summary={incident.summary} facts={[{ label: 'Incident ID', value: incident.id }, { label: 'Building', value: incident.building_id }, { label: 'Equipment', value: incident.equipment_id }, { label: 'Severity', value: incident.severity }, { label: 'Anomaly score', value: incident.anomaly_score.toFixed(4) }, { label: 'Window', value: `${formatTimestamp(incident.started_at)} – ${formatTimestamp(incident.ended_at)}` }]} detail={incident.evidence.map((item) => `${item.metric}: ${item.value} ${item.unit ?? ''} (${item.aggregation})`).join(' · ')} />
}

function RealOverviewLayout({ summary, facts, detail }: { summary: string; facts: Array<{ label: string; value: string }>; detail?: string }) {
  return <div className="overview-layout"><div className="stage-summary"><Info size={18} /><div><h3>Backend result</h3><p>{summary}</p></div></div><div className="fact-grid">{facts.map((fact) => <div className="fact-card" key={fact.label}><span>{fact.label}</span><strong>{fact.value}</strong></div>)}</div>{detail && <div className="stage-rule"><Database size={16} /><span>{detail}</span></div>}</div>
}

function RealInputs({ stageId, results }: { stageId: PipelineStageId; results: RealPipelineResults }) {
  if (stageId === 'generate') return results.manifest ? <JsonBlock title="Experiment configuration" value={results.manifest.config} source="real backend" /> : <AwaitingBackend />
  if (stageId === 'features') return results.rawTelemetry ? <JsonBlock title="Raw telemetry summary" value={{ total_rows: results.rawTelemetry.total_rows, columns: results.rawTelemetry.columns }} source="real backend" /> : <AwaitingBackend />
  if (stageId === 'detection') return results.features ? <JsonBlock title="Feature input summary" value={{ total_rows: results.features.total_rows, columns: results.features.columns }} source="real backend" /> : <AwaitingBackend />
  return results.events ? <DataTable title="Detected events" columns={results.events.columns} rows={results.events.rows.slice(0, 12)} /> : <AwaitingBackend />
}

function RealOutputs({ stageId, results }: { stageId: PipelineStageId; results: RealPipelineResults }) {
  if (stageId === 'generate') return results.rawTelemetry ? <DataTable title={`Raw telemetry preview (${results.rawTelemetry.total_rows.toLocaleString()} total rows)`} columns={results.rawTelemetry.columns} rows={results.rawTelemetry.rows.slice(0, 12)} /> : <AwaitingBackend />
  if (stageId === 'features') return results.features ? <DataTable title={`Feature table preview (${results.features.total_rows.toLocaleString()} total rows)`} columns={results.features.columns} rows={results.features.rows.slice(0, 12)} /> : <AwaitingBackend />
  if (stageId === 'detection') {
    if (!results.anomalyScores || !results.events) return <AwaitingBackend />
    return <div className="real-output-stack"><DataTable title="Anomaly score preview" columns={results.anomalyScores.columns} rows={results.anomalyScores.rows.slice(0, 10)} /><DataTable title="Detected events" columns={results.events.columns} rows={results.events.rows.slice(0, 10)} /></div>
  }
  return results.incidentStage ? <JsonBlock title="OperationalIncident" value={results.incidentStage.incident} source="real backend" /> : <AwaitingBackend />
}

function RealVisuals({ stageId, results }: { stageId: PipelineStageId; results: RealPipelineResults }) {
  if (stageId === 'generate') {
    const data = results.rawTelemetry ? pivotRawTelemetry(results.rawTelemetry.rows) : []
    return data.length ? <RealTelemetryVisual data={data} title="Raw telemetry preview" /> : <AwaitingBackend />
  }
  if (stageId === 'features') {
    const data = results.features ? featureChartRows(results.features.rows) : []
    return data.length ? <RealTelemetryVisual data={data} title="Engineered feature series" /> : <AwaitingBackend />
  }
  if (stageId === 'detection') {
    const data = results.anomalyScores ? anomalyChartRows(results.anomalyScores.rows) : []
    const threshold = results.detectionSummary?.threshold
    if (!data.length || threshold === undefined) return <AwaitingBackend />
    return <ChartFrame title="Anomaly score by timestamp" legend={`Backend threshold: ${threshold.toFixed(4)}`}><ResponsiveContainer width="100%" height="100%"><AreaChart data={data}><defs><linearGradient id="realScoreFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#b9db75" stopOpacity={0.35} /><stop offset="1" stopColor="#b9db75" stopOpacity={0} /></linearGradient></defs><CartesianGrid stroke="#2d3940" vertical={false} /><XAxis dataKey="label" tick={{ fill: '#89969c', fontSize: 10 }} axisLine={false} tickLine={false} minTickGap={30} /><YAxis domain={['auto', 'auto']} tick={{ fill: '#89969c', fontSize: 10 }} axisLine={false} tickLine={false} /><Tooltip contentStyle={{ background: '#10191d', border: '1px solid #344148', borderRadius: 8 }} /><ReferenceLine y={threshold} stroke="#e19a65" strokeDasharray="5 4" label={{ value: 'threshold', fill: '#e19a65', fontSize: 10 }} /><Area type="monotone" dataKey="anomalyScore" stroke="#b9db75" fill="url(#realScoreFill)" strokeWidth={2.5} /></AreaChart></ResponsiveContainer></ChartFrame>
  }
  const incident = results.incidentStage?.incident
  return incident ? <div className="incident-evidence-visual"><h3>Incident evidence</h3>{incident.evidence.map((item) => <div key={`${item.metric}-${item.aggregation}`}><span>{item.metric}</span><strong>{item.value.toLocaleString()} {item.unit ?? ''}</strong><small>{item.aggregation}</small></div>)}</div> : <AwaitingBackend />
}

interface RealChartPoint { label: string; powerKw?: number; heatingValvePct?: number; supplyAirTempC?: number }

function pivotRawTelemetry(rows: Array<Record<string, unknown>>): RealChartPoint[] {
  const byTimestamp = new Map<string, RealChartPoint>()
  const fields: Record<string, keyof RealChartPoint> = { 'AHU01-POWER': 'powerKw', 'AHU01-HEAT-VALVE': 'heatingValvePct', 'AHU01-SUPPLY-TEMP': 'supplyAirTempC' }
  rows.forEach((row) => {
    const timestamp = String(row.timestamp ?? '')
    const field = fields[String(row.sensor_id ?? '')]
    if (!timestamp || !field) return
    const point = byTimestamp.get(timestamp) ?? { label: formatTimestamp(timestamp) }
    const value = Number(row.value)
    if (!Number.isNaN(value)) Object.assign(point, { [field]: value })
    byTimestamp.set(timestamp, point)
  })
  return Array.from(byTimestamp.values())
}

function featureChartRows(rows: Array<Record<string, unknown>>): RealChartPoint[] {
  return rows.map((row) => ({ label: formatTimestamp(String(row.timestamp ?? '')), powerKw: Number(row.power_kw), heatingValvePct: Number(row.heating_valve_pct), supplyAirTempC: Number(row.supply_air_temp_c) }))
}

function anomalyChartRows(rows: Array<Record<string, unknown>>) {
  return rows.map((row) => ({ label: formatTimestamp(String(row.timestamp ?? '')), anomalyScore: Number(row.anomaly_score) })).filter((row) => !Number.isNaN(row.anomalyScore))
}

function formatTimestamp(timestamp: string): string {
  return timestamp.replace('T', ' ').slice(0, 16)
}

function RealTelemetryVisual({ data, title }: { data: RealChartPoint[]; title: string }) {
  return <ChartFrame title={title} legend="Power kW and valve % share the left scale; supply air °C uses the right scale."><ResponsiveContainer width="100%" height="100%"><LineChart data={data}><CartesianGrid stroke="#2d3940" vertical={false} /><XAxis dataKey="label" tick={{ fill: '#89969c', fontSize: 10 }} axisLine={false} tickLine={false} minTickGap={30} /><YAxis yAxisId="left" tick={{ fill: '#89969c', fontSize: 10 }} axisLine={false} tickLine={false} /><YAxis yAxisId="right" orientation="right" domain={['auto', 'auto']} tick={{ fill: '#89969c', fontSize: 10 }} axisLine={false} tickLine={false} /><Tooltip contentStyle={{ background: '#10191d', border: '1px solid #344148', borderRadius: 8 }} /><Line yAxisId="left" dataKey="powerKw" name="Power kW" stroke="#b9db75" strokeWidth={2} dot={false} connectNulls /><Line yAxisId="left" dataKey="heatingValvePct" name="Valve %" stroke="#e19a65" strokeWidth={2} dot={false} connectNulls /><Line yAxisId="right" dataKey="supplyAirTempC" name="Supply °C" stroke="#62b2ce" strokeWidth={2} dot={false} connectNulls /></LineChart></ResponsiveContainer></ChartFrame>
}

function AwaitingBackend() {
  return <div className="real-empty"><Database size={22} /><h3>Backend result not available</h3><p>Run this stage to inspect its real response and artifacts.</p></div>
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

  const messages: Partial<Record<PipelineStageId, string>> = {
    investigation: 'The agent follows a read-only evidence trail. Sensor discovery happens before telemetry access, and operational facts come from tools.',
    rag: 'Retrieves a small set of relevant operating procedures to contextualize the observed evidence without treating documentation as proof.',
    assessment: 'Returns a typed assessment that distinguishes the likely issue from confirmed evidence and recommends a bounded next step.',
    approval: '',
    'work-order': 'A write action is available only after explicit approval. This prototype displays the resulting record but never calls the Python server.',
  }
  return (
    <div className="overview-layout">
      <div className="stage-summary"><Info size={18} /><div><h3>What this stage does</h3><p>{messages[stage.id] ?? ''}</p></div></div>
      <div className="fact-grid">{(stageFacts[stage.id] ?? []).map((fact) => <div className="fact-card" key={fact.label}><span>{fact.label}</span><strong>{fact.value}</strong></div>)}</div>
      <div className="stage-rule"><AlertCircle size={16} /><span>{stage.id === 'work-order' ? 'Write boundary: requires an approved decision.' : stage.id === 'assessment' ? 'Output is schema-validated before presentation.' : 'All values shown here are local mock data for the frontend prototype.'}</span></div>
    </div>
  )
}

function Inputs({ stageId, approvalDecision }: { stageId: PipelineStageId; approvalDecision: 'waiting' | 'approved' | 'rejected' }) {
  if (stageId === 'investigation') return <JsonBlock title="Incident context" value={{ building_id: 'BLDG-001', equipment_id: 'AHU-001', zone_id: 'ZONE-003', incident_window: ['2026-01-15T01:00:00', '2026-01-15T05:00:00'], constraints: ['read-only investigation', 'do not invent evidence'] }} />
  if (stageId === 'rag') return <div className="query-card"><Search size={17} /><div><span>Retrieval query</span><code>AHU heating valve high command low supply temperature after-hours fan operation actuator response</code></div></div>
  if (stageId === 'assessment') return <TagList title="Evidence bundle" tags={['20 telemetry readings', '2 maintenance records', '3 tenant complaints', '3 RAG chunks']} />
  if (stageId === 'approval') return <JsonBlock title="Proposed work order" value={{ ...operationsView.proposedWorkOrder, status: approvalDecision }} />
  return <JsonBlock title="Approval token" value={{ approved_by: approvalDecision === 'approved' ? 'demo.operator' : null, decision: approvalDecision, action_authorized: approvalDecision === 'approved', proposed_action: 'create_work_order' }} />
}

function Outputs({ stageId, approvalDecision }: { stageId: PipelineStageId; approvalDecision: 'waiting' | 'approved' | 'rejected' }) {
  if (stageId === 'investigation') return <ToolCalls />
  if (stageId === 'rag') return <RagResults />
  if (stageId === 'assessment') return <JsonBlock title="InvestigationAssessment" value={{ likely_issue: operationsView.assessment.likelyIssue, confidence: operationsView.assessment.confidence, telemetry_findings: operationsView.assessment.telemetryFindings, maintenance_findings: operationsView.assessment.maintenanceFindings, occupant_impact: operationsView.assessment.occupantImpact, recommended_next_step: operationsView.assessment.recommendedNextStep }} />
  if (stageId === 'approval') return <JsonBlock title="Decision state" value={{ status: approvalDecision, action_authorized: approvalDecision === 'approved', recorded_locally: true }} />
  return <JsonBlock title="WorkOrder" value={{ id: approvalDecision === 'approved' ? 'WO-DEMO-1042' : null, building_id: 'BLDG-001', equipment_id: 'AHU-001', status: approvalDecision === 'approved' ? 'open' : 'not_created', note: 'Frontend mock only' }} />
}

function Visuals({ stageId }: { stageId: PipelineStageId }) {
  if (stageId === 'investigation') return <EvidenceCoverage />
  if (stageId === 'rag') return <RetrievalVisual />
  if (stageId === 'assessment') return <ConfidenceVisual />
  return <FlowBoundary stageId={stageId} />
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

function JsonBlock({ title, value, source = 'mock payload' }: { title: string; value: unknown; source?: string }) {
  return <div className="json-block"><div className="code-heading"><span><Database size={14} />{title}</span><small>{source}</small></div><pre>{JSON.stringify(value, null, 2)}</pre></div>
}

function TagList({ title, tags }: { title: string; tags: string[] }) {
  return <div className="tag-list"><h3>{title}</h3><div>{tags.map((tag) => <code key={tag}>{tag}</code>)}</div></div>
}

function DataTable({ title, columns, rows }: { title: string; columns: string[]; rows: Array<Record<string, unknown>> }) {
  return <div className="data-table-wrap"><h3>{title}</h3><div className="table-scroll"><table><thead><tr>{columns.map((column) => <th key={column}>{column}</th>)}</tr></thead><tbody>{rows.map((row, index) => <tr key={index}>{columns.map((column) => <td key={column}>{row[column] == null ? '—' : String(row[column])}</td>)}</tr>)}</tbody></table></div></div>
}

function ChartFrame({ title, legend, children }: { title: string; legend: string; children: React.ReactNode }) {
  return <div className="lab-chart-frame"><div><h3>{title}</h3><p>{legend}</p></div><div className="lab-chart">{children}</div></div>
}
