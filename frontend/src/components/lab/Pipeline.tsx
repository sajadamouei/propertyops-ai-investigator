import { Check, ChevronRight, Circle, Clock3, Minus, Play, X } from 'lucide-react'
import type { PipelineStage, PipelineStageId, PipelineStageStatus } from '../../types'

function StatusIcon({ status }: { status: PipelineStageStatus }) {
  if (status === 'complete') return <Check size={14} />
  if (status === 'running') return <Play size={12} fill="currentColor" />
  if (status === 'waiting') return <Clock3 size={13} />
  if (status === 'skipped') return <Minus size={14} />
  if (status === 'failed') return <X size={14} />
  return <Circle size={10} fill={status === 'ready' ? 'currentColor' : 'none'} />
}

export function Pipeline({ stages, selectedId, onSelect }: { stages: PipelineStage[]; selectedId: PipelineStageId; onSelect: (id: PipelineStageId) => void }) {
  return (
    <section className="pipeline-section">
      <div className="section-label"><span>Execution flow</span><small>Click any stage to inspect it</small></div>
      <div className="pipeline-scroll">
        <div className="pipeline" role="list" aria-label="AI investigation pipeline">
          {stages.map((stage, index) => (
            <div className="pipeline-pair" key={stage.id}>
              <button className={`pipeline-node node-${stage.status} ${selectedId === stage.id ? 'selected' : ''}`} onClick={() => onSelect(stage.id)} role="listitem" aria-current={selectedId === stage.id ? 'step' : undefined}>
                <span className="node-index">{String(index + 1).padStart(2, '0')}</span>
                <span className="node-name">{stage.shortLabel}</span>
                <span className="node-status"><StatusIcon status={stage.status} />{stage.status.replace('_', ' ')}</span>
              </button>
              {index < stages.length - 1 && <ChevronRight className="pipeline-arrow" size={16} />}
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
