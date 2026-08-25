import { AlertCircle, Box, CheckCircle2, Database, FileSearch, Gauge, Info, Search, Wrench } from 'lucide-react'
import { Area, AreaChart, Bar, BarChart, CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { OperationalInvestigationResponse, RagStageResponse, RealPipelineResults } from '../../api/propertyOpsApi'
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

export function StageInspector({ stage, activeTab, onTabChange, approvalDecision, onApprovalDecision, backendResults, stageError }: StageInspectorProps) {
  return (
    <section className="inspector panel-dark">
      <header className="inspector-header">
        <div><span className="lab-eyebrow">Stage inspector</span><div className="inspector-title"><h2>{stage.label}</h2><StageStatusBadge status={stage.status} /></div><p>{stage.description}</p></div>
        <div className="inspector-source"><span className="source-badge source-real">REAL BACKEND</span><span className="inspector-stage-id">{stage.id}</span></div>
      </header>
      <div className="inspector-tabs" role="tablist">
        {tabs.map((tab) => <button key={tab} role="tab" aria-selected={activeTab === tab} className={activeTab === tab ? 'active' : ''} onClick={() => onTabChange(tab)}>{tab}</button>)}
      </div>
      <div className="inspector-body" role="tabpanel">
        {stageError && <div className="stage-error" role="alert"><AlertCircle size={16} /><span>{stageError}</span></div>}
        <RealStageContent stage={stage} activeTab={activeTab} results={backendResults} approvalDecision={approvalDecision} onApprovalDecision={onApprovalDecision} />
      </div>
    </section>
  )
}

function RealStageContent({ stage, activeTab, results, approvalDecision, onApprovalDecision }: { stage: PipelineStage; activeTab: InspectorTab; results: RealPipelineResults; approvalDecision: 'waiting' | 'approved' | 'rejected'; onApprovalDecision: (decision: 'approved' | 'rejected') => void }) {
  if (activeTab === 'overview') return <RealOverview stage={stage} results={results} approvalDecision={approvalDecision} onApprovalDecision={onApprovalDecision} />
  if (activeTab === 'inputs') return <RealInputs stageId={stage.id} results={results} />
  if (activeTab === 'outputs') return <RealOutputs stageId={stage.id} results={results} />
  return <RealVisuals stageId={stage.id} results={results} />
}

function RealOverview({ stage, results, approvalDecision, onApprovalDecision }: { stage: PipelineStage; results: RealPipelineResults; approvalDecision: 'waiting' | 'approved' | 'rejected'; onApprovalDecision: (decision: 'approved' | 'rejected') => void }) {
  const stageId = stage.id
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
  if (stageId === 'investigation') {
    const investigation = results.investigation
    if (!investigation) return <AwaitingBackend />
    return <RealOverviewLayout summary={investigation.summary} facts={[{ label: 'Telemetry findings', value: String(investigation.telemetry_findings.length) }, { label: 'Maintenance findings', value: String(investigation.maintenance_findings.length) }, { label: 'Occupant impacts', value: String(investigation.occupant_impact.length) }, { label: 'MCP trace entries', value: String(results.mcpTrace.length) }]} />
  }
  if (stageId === 'rag') {
    if (!results.ragStage) return <AwaitingBackend />
    return <RealOverviewLayout summary="Focused retrieval queries are searched separately, then merged and deduplicated to preserve coverage across the operational incident." facts={[{ label: 'Retrieval queries', value: String(results.ragStage.retrieval_queries.length) }, { label: 'Embedding model', value: results.ragStage.embedding_model }, { label: 'Retrieved chunks', value: String(results.ragStage.results.length) }]} detail={`One operational incident → ${results.ragStage.retrieval_queries.length} focused retrieval queries → FAISS search → merge/deduplicate → ${results.ragStage.results.length} final technical context chunks`} />
  }
  if (stageId === 'assessment') {
    const assessment = results.assessment
    if (!assessment) return <AwaitingBackend />
    return <RealOverviewLayout summary={assessment.likely_issue} facts={[{ label: 'Confidence', value: `${Math.round(assessment.confidence * 100)}%` }, { label: 'Telemetry findings', value: String(assessment.telemetry_findings.length) }, { label: 'Maintenance findings', value: String(assessment.maintenance_findings.length) }, { label: 'Occupant impacts', value: String(assessment.occupant_impact.length) }]} detail={assessment.recommended_next_step} />
  }
  if (stageId === 'approval') {
    if (results.approval) {
      return <RealOverviewLayout summary={results.approval.approved ? 'The operator approved the proposed maintenance action.' : 'The operator rejected the proposed maintenance action.'} facts={[{ label: 'Decision', value: results.approval.approved ? 'Approved' : 'Rejected' }, { label: 'Decided at', value: formatTimestamp(results.approval.decided_at) }]} detail={results.approval.rationale ?? undefined} />
    }
    const prompt = results.approvalRequest
    if (!prompt) return <AwaitingBackend />
    return <div className="approval-inspector"><div className="approval-inspector-copy"><span className="warning-icon"><Wrench size={20} /></span><div><h3>{prompt.question}</h3><p>{prompt.recommended_next_step}</p><div className="mini-meta"><span>{prompt.incident_id}</span><span>{prompt.equipment_id}</span><span>{Math.round(prompt.confidence * 100)}% confidence</span></div></div></div><div className="approval-inspector-actions">{approvalDecision !== 'waiting' ? <div className={`lab-decision decision-${approvalDecision}`}><CheckCircle2 size={17} /> Decision: {approvalDecision}</div> : stage.status === 'waiting' ? <><button className="button button-lime" onClick={() => onApprovalDecision('approved')}>Approve work order</button><button className="button button-ghost-dark" onClick={() => onApprovalDecision('rejected')}>Reject</button></> : <div className="lab-decision">Available when the pipeline reaches approval</div>}</div></div>
  }
  if (stageId === 'work-order') {
    if (!results.approval) return <div className="real-empty"><Wrench size={22} /><h3>Awaiting operator decision</h3><p>A work order can only be created after the approval stage completes.</p></div>
    if (!results.approval.approved || !results.workOrder) return <div className="real-empty"><CheckCircle2 size={22} /><h3>No work order created</h3><p>The proposed action was rejected, so the backend did not create a work order.</p></div>
    const workOrder = results.workOrder.work_order
    return <RealOverviewLayout summary={workOrder.description} facts={[{ label: 'Work order', value: workOrder.id }, { label: 'Status', value: workOrder.status }, { label: 'Building', value: workOrder.building_id }, { label: 'Equipment', value: workOrder.equipment_id }]} detail={`Created ${formatTimestamp(workOrder.created_at)}`} />
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
  if (stageId === 'incident') return results.events ? <DataTable title="Detected events" columns={results.events.columns} rows={results.events.rows.slice(0, 12)} /> : <AwaitingBackend />
  if (stageId === 'investigation') return results.incidentStage?.incident ? <JsonBlock title="OperationalIncident" value={results.incidentStage.incident} source="real backend" /> : <AwaitingBackend />
  if (stageId === 'rag') return results.ragStage ? <RagInputs rag={results.ragStage} /> : <AwaitingBackend />
  if (stageId === 'assessment') return results.investigation && results.ragStage ? <div className="real-output-stack"><JsonBlock title="OperationalInvestigation" value={results.investigation} source="real backend" /><JsonBlock title="RAG context summary" value={{ query: results.ragStage.query, retrieval_queries: results.ragStage.retrieval_queries, retrieved_chunks: results.ragStage.results.length, sources: results.ragStage.results.map((result) => result.source) }} source="real backend" /></div> : <AwaitingBackend />
  if (stageId === 'approval') return results.approvalRequest ? <JsonBlock title="WorkflowApprovalPrompt" value={results.approvalRequest} source="real backend" /> : <AwaitingBackend />
  return results.approval ? <JsonBlock title="ApprovalRecord" value={results.approval} source="real backend" /> : <AwaitingBackend />
}

function RealOutputs({ stageId, results }: { stageId: PipelineStageId; results: RealPipelineResults }) {
  if (stageId === 'generate') return results.rawTelemetry ? <DataTable title={`Raw telemetry preview (${results.rawTelemetry.total_rows.toLocaleString()} total rows)`} columns={results.rawTelemetry.columns} rows={results.rawTelemetry.rows.slice(0, 12)} /> : <AwaitingBackend />
  if (stageId === 'features') return results.features ? <DataTable title={`Feature table preview (${results.features.total_rows.toLocaleString()} total rows)`} columns={results.features.columns} rows={results.features.rows.slice(0, 12)} /> : <AwaitingBackend />
  if (stageId === 'detection') {
    if (!results.anomalyScores || !results.events) return <AwaitingBackend />
    return <div className="real-output-stack"><DataTable title="Anomaly score preview" columns={results.anomalyScores.columns} rows={results.anomalyScores.rows.slice(0, 10)} /><DataTable title="Detected events" columns={results.events.columns} rows={results.events.rows.slice(0, 10)} /></div>
  }
  if (stageId === 'incident') return results.incidentStage ? <JsonBlock title="OperationalIncident" value={results.incidentStage.incident} source="real backend" /> : <AwaitingBackend />
  if (stageId === 'investigation') return results.investigation ? <div className="real-output-stack"><JsonBlock title="OperationalInvestigation" value={results.investigation} source="real backend" /><JsonBlock title="MCP trace" value={results.mcpTrace} source="real backend" /></div> : <AwaitingBackend />
  if (stageId === 'rag') return results.ragStage ? <RagResults rag={results.ragStage} /> : <AwaitingBackend />
  if (stageId === 'assessment') return results.assessment ? <JsonBlock title="InvestigationAssessment" value={results.assessment} source="real backend" /> : <AwaitingBackend />
  if (stageId === 'approval') return results.approval ? <JsonBlock title="ApprovalRecord" value={results.approval} source="real backend" /> : results.approvalRequest ? <JsonBlock title="Pending approval request" value={results.approvalRequest} source="real backend" /> : <AwaitingBackend />
  if (!results.approval) return <AwaitingBackend />
  return results.workOrder ? <JsonBlock title="WorkOrderCreationResult" value={results.workOrder} source="real backend" /> : <JsonBlock title="WorkOrderCreationResult" value={{ created: false, work_order: null, reason: 'Operator rejected the proposed action.' }} source="real backend" />
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
    return <ChartFrame title="Anomaly score by timestamp" legend={`Backend threshold: ${threshold.toFixed(4)}`}><ResponsiveContainer width="100%" height="100%"><AreaChart data={data}><defs><linearGradient id="realScoreFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#b9db75" stopOpacity={0.35} /><stop offset="1" stopColor="#b9db75" stopOpacity={0} /></linearGradient></defs><CartesianGrid stroke="#2d3940" vertical={false} /><XAxis dataKey="label" tick={{ fill: '#89969c', fontSize: 12 }} axisLine={false} tickLine={false} minTickGap={30} /><YAxis domain={['auto', 'auto']} tick={{ fill: '#89969c', fontSize: 12 }} axisLine={false} tickLine={false} /><Tooltip contentStyle={{ background: '#10191d', border: '1px solid #344148', borderRadius: 8 }} /><ReferenceLine y={threshold} stroke="#e19a65" strokeDasharray="5 4" label={{ value: 'threshold', fill: '#e19a65', fontSize: 12 }} /><Area type="monotone" dataKey="anomalyScore" stroke="#b9db75" fill="url(#realScoreFill)" strokeWidth={2.5} /></AreaChart></ResponsiveContainer></ChartFrame>
  }
  if (stageId === 'investigation') return results.investigation ? <EvidenceCoverage investigation={results.investigation} /> : <AwaitingBackend />
  if (stageId === 'rag') return results.ragStage ? <RetrievalVisual rag={results.ragStage} /> : <AwaitingBackend />
  if (stageId === 'assessment') return results.assessment ? <ConfidenceVisual confidence={results.assessment.confidence} /> : <AwaitingBackend />
  if (stageId === 'approval' || stageId === 'work-order') return <FlowBoundary stageId={stageId} />
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
  return <ChartFrame title={title} legend="Power kW and valve % share the left scale; supply air °C uses the right scale."><ResponsiveContainer width="100%" height="100%"><LineChart data={data}><CartesianGrid stroke="#2d3940" vertical={false} /><XAxis dataKey="label" tick={{ fill: '#89969c', fontSize: 12 }} axisLine={false} tickLine={false} minTickGap={30} /><YAxis yAxisId="left" tick={{ fill: '#89969c', fontSize: 12 }} axisLine={false} tickLine={false} /><YAxis yAxisId="right" orientation="right" domain={['auto', 'auto']} tick={{ fill: '#89969c', fontSize: 12 }} axisLine={false} tickLine={false} /><Tooltip contentStyle={{ background: '#10191d', border: '1px solid #344148', borderRadius: 8 }} /><Line yAxisId="left" dataKey="powerKw" name="Power kW" stroke="#b9db75" strokeWidth={2} dot={false} connectNulls /><Line yAxisId="left" dataKey="heatingValvePct" name="Valve %" stroke="#e19a65" strokeWidth={2} dot={false} connectNulls /><Line yAxisId="right" dataKey="supplyAirTempC" name="Supply °C" stroke="#62b2ce" strokeWidth={2} dot={false} connectNulls /></LineChart></ResponsiveContainer></ChartFrame>
}

function AwaitingBackend() {
  return <div className="real-empty"><Database size={22} /><h3>Backend result not available</h3><p>Run this stage to inspect its real response and artifacts.</p></div>
}

function EvidenceCoverage({ investigation }: { investigation: OperationalInvestigationResponse }) {
  const data = [{ name: 'Telemetry', items: investigation.telemetry_findings.length }, { name: 'Maintenance', items: investigation.maintenance_findings.length }, { name: 'Occupant impact', items: investigation.occupant_impact.length }]
  return <ChartFrame title="Evidence collected by source" legend="All requested operational sources were checked."><ResponsiveContainer width="100%" height="100%"><BarChart data={data} layout="vertical" margin={{ left: 20 }}><CartesianGrid stroke="#2d3940" horizontal={false} /><XAxis type="number" tick={{ fill: '#89969c', fontSize: 12 }} axisLine={false} tickLine={false} /><YAxis type="category" dataKey="name" tick={{ fill: '#c9d2d5', fontSize: 12 }} axisLine={false} tickLine={false} width={88} /><Tooltip contentStyle={{ background: '#10191d', border: '1px solid #344148', borderRadius: 8 }} /><Bar dataKey="items" fill="#b9db75" radius={[0, 4, 4, 0]} barSize={18} /></BarChart></ResponsiveContainer></ChartFrame>
}

function RetrievalVisual({ rag }: { rag: RagStageResponse }) {
  const data = rag.results.map((result, index) => ({ label: `#${index + 1} ${result.source}`, score: result.score }))
  return <ChartFrame title="Retrieval relevance" legend="Backend similarity score by retrieved document chunk."><ResponsiveContainer width="100%" height="100%"><BarChart data={data} layout="vertical" margin={{ left: 30 }}><CartesianGrid stroke="#2d3940" horizontal={false} /><XAxis type="number" domain={[0, 1]} tick={{ fill: '#89969c', fontSize: 12 }} axisLine={false} tickLine={false} /><YAxis type="category" dataKey="label" tick={{ fill: '#89969c', fontSize: 12 }} axisLine={false} tickLine={false} width={165} /><Tooltip contentStyle={{ background: '#10191d', border: '1px solid #344148', borderRadius: 8 }} /><Bar dataKey="score" fill="#b9db75" radius={[0, 4, 4, 0]} barSize={22} /></BarChart></ResponsiveContainer></ChartFrame>
}

function ConfidenceVisual({ confidence }: { confidence: number }) {
  const percent = Math.round(confidence * 100)
  return <div className="confidence-visual"><div className="confidence-gauge"><Gauge size={38} /><strong>{percent}%</strong><span>Assessment confidence</span></div><div className="confidence-breakdown"><div><span>Backend assessment confidence</span><i><b style={{ width: `${percent}%` }} /></i><strong>{percent}%</strong></div></div></div>
}

function FlowBoundary({ stageId }: { stageId: PipelineStageId }) {
  return <div className="flow-boundary"><div><Box size={20} /><strong>Assessment</strong></div><span className="boundary-line"><em>explicit operator decision</em></span><div className={stageId === 'work-order' ? 'active' : ''}><Wrench size={20} /><strong>Work order</strong></div></div>
}

function RagInputs({ rag }: { rag: RagStageResponse }) {
  return <div className="real-output-stack"><div className="query-card"><Search size={17} /><div><span>Overall query</span><code>{rag.query}</code></div></div>{rag.retrieval_queries.map((query, index) => <div className="query-card" key={`${index}-${query}`}><Search size={17} /><div><span>Query {index + 1}</span><code>{query}</code></div></div>)}</div>
}

function RagResults({ rag }: { rag: RagStageResponse }) {
  if (!rag.results.length) return <div className="real-empty"><FileSearch size={22} /><h3>No chunks retrieved</h3><p>The backend completed RAG without returning technical context.</p></div>
  return <div className="rag-results">{rag.results.map((item, index) => <article className="rag-card" key={item.chunk_id}><div className="rag-rank">{String(index + 1).padStart(2, '0')}</div><div><div className="rag-heading"><span><FileSearch size={14} />{item.source}</span><strong>{item.score.toFixed(4)}</strong></div><small>{item.chunk_id}</small><p>{item.text}</p></div></article>)}</div>
}

function JsonBlock({ title, value, source = 'real backend' }: { title: string; value: unknown; source?: string }) {
  return <div className="json-block"><div className="code-heading"><span><Database size={14} />{title}</span><small>{source}</small></div><pre>{JSON.stringify(value, null, 2)}</pre></div>
}

function DataTable({ title, columns, rows }: { title: string; columns: string[]; rows: Array<Record<string, unknown>> }) {
  return <div className="data-table-wrap"><h3>{title}</h3><div className="table-scroll"><table><thead><tr>{columns.map((column) => <th key={column}>{column}</th>)}</tr></thead><tbody>{rows.map((row, index) => <tr key={index}>{columns.map((column) => <td key={column}>{row[column] == null ? '—' : String(row[column])}</td>)}</tr>)}</tbody></table></div></div>
}

function ChartFrame({ title, legend, children }: { title: string; legend: string; children: React.ReactNode }) {
  return <div className="lab-chart-frame"><div><h3>{title}</h3><p>{legend}</p></div><div className="lab-chart">{children}</div></div>
}
