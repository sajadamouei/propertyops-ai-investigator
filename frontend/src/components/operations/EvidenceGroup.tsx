import { Clock3 } from 'lucide-react'
import type { EvidenceItem } from '../../types'

export function EvidenceGroup({ title, subtitle, items }: { title: string; subtitle: string; items: EvidenceItem[] }) {
  return (
    <div className="evidence-group">
      <div className="evidence-group-heading">
        <h3>{title}</h3>
        <span>{subtitle}</span>
      </div>
      <div className="evidence-list">
        {items.map((item) => (
          <article className="evidence-item" key={item.id}>
            <div className="evidence-dot" />
            <div>
              <div className="evidence-title-row"><strong>{item.title}</strong>{item.value && <span>{item.value}</span>}</div>
              <p>{item.detail}</p>
              {item.timestamp && <small><Clock3 size={12} />{item.timestamp}</small>}
            </div>
          </article>
        ))}
      </div>
    </div>
  )
}
