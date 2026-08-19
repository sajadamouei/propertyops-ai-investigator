import type { PipelineStageStatus } from '../../types'

export function SeverityBadge({ severity }: { severity: string }) {
  return <span className={`badge severity-${severity}`}>{severity} severity</span>
}

export function StageStatusBadge({ status }: { status: PipelineStageStatus }) {
  return <span className={`status-badge status-${status}`}>{status.replace('_', ' ')}</span>
}
