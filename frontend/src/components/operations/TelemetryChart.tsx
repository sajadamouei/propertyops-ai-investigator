import { useId, useState } from 'react'
import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceArea,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { TelemetryPoint } from '../../types'

type Metric = 'powerKw' | 'heatingValvePct' | 'supplyAirTempC'

const metricConfig: Record<Metric, { label: string; unit: string; color: string; domain: [number, number] }> = {
  powerKw: { label: 'Power', unit: 'kW', color: '#2559b7', domain: [0, 170] },
  heatingValvePct: { label: 'Heating valve', unit: '%', color: '#b75824', domain: [0, 110] },
  supplyAirTempC: { label: 'Supply air', unit: '°C', color: '#168275', domain: [10, 22] },
}

export function TelemetryChart({ data, incidentStart, incidentEnd }: { data: TelemetryPoint[]; incidentStart: string; incidentEnd: string }) {
  const [metric, setMetric] = useState<Metric>('powerKw')
  const gradientId = useId().replace(/:/g, '')
  const config = metricConfig[metric]
  const incidentStartLabel = data.find((point) => point.timestamp === incidentStart)?.label
  const incidentEndLabel = data.find((point) => point.timestamp === incidentEnd)?.label

  return (
    <section className="panel telemetry-panel">
      <div className="panel-heading telemetry-heading">
        <div>
          <span className="eyebrow">Live evidence</span>
          <h2>Equipment telemetry</h2>
        </div>
        <div className="segmented-control" aria-label="Telemetry metric">
          {(Object.keys(metricConfig) as Metric[]).map((key) => (
            <button key={key} className={metric === key ? 'active' : ''} onClick={() => setMetric(key)}>{metricConfig[key].label}</button>
          ))}
        </div>
      </div>
      <div className="chart-key">
        <span><i style={{ background: config.color }} />{config.label} ({config.unit})</span>
        <span><i className="incident-key" />Incident window</span>
      </div>
      <div className="chart-wrap operations-chart">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 12, right: 12, left: -12, bottom: 0 }}>
            <defs>
              <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#d98462" stopOpacity={0.18} />
                <stop offset="100%" stopColor="#d98462" stopOpacity={0.04} />
              </linearGradient>
            </defs>
            <CartesianGrid stroke="#e7e9e5" strokeDasharray="3 4" vertical={false} />
            <XAxis dataKey="label" tick={{ fontSize: 11, fill: '#69706a' }} axisLine={false} tickLine={false} interval={1} />
            <YAxis domain={config.domain} tick={{ fontSize: 11, fill: '#69706a' }} axisLine={false} tickLine={false} unit={config.unit === '°C' ? '°' : ''} />
            <Tooltip content={<TelemetryTooltip metric={metric} />} />
            {incidentStartLabel && incidentEndLabel && <ReferenceArea x1={incidentStartLabel} x2={incidentEndLabel} fill={`url(#${gradientId})`} />}
            <Line type="monotone" dataKey={metric} stroke={config.color} strokeWidth={2.5} dot={{ r: 3, strokeWidth: 2, fill: '#fff' }} activeDot={{ r: 5 }} />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <p className="chart-caption">Telemetry shown for the real incident window, with two hours of surrounding operating context.</p>
    </section>
  )
}

function TelemetryTooltip({ active, payload, metric }: { active?: boolean; payload?: Array<{ value: number; payload: TelemetryPoint }>; metric: Metric }) {
  if (!active || !payload?.length) return null
  const point = payload[0]
  const config = metricConfig[metric]
  return (
    <div className="chart-tooltip">
      <strong>{point.payload.label}</strong>
      <span>{config.label}: {point.value.toFixed(1)} {config.unit}</span>
      {point.payload.isAnomaly && <em>Anomaly detected</em>}
    </div>
  )
}
