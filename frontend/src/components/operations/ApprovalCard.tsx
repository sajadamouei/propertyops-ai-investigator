import { Check, ClipboardCheck, ShieldCheck, X } from 'lucide-react'
import type { ProposedWorkOrder } from '../../types'

export function ApprovalCard({ workOrder, onDecision }: { workOrder: ProposedWorkOrder; onDecision: (decision: 'approved' | 'rejected') => void }) {
  const decided = workOrder.status !== 'waiting'

  return (
    <section className={`approval-card approval-${workOrder.status}`}>
      <div className="approval-icon">{workOrder.status === 'approved' ? <Check size={22} /> : workOrder.status === 'rejected' ? <X size={22} /> : <ClipboardCheck size={22} />}</div>
      <div className="approval-main">
        <div className="approval-heading">
          <div>
            <span className="eyebrow">Human approval required</span>
            <h2>{decided ? `Work order ${workOrder.status}` : 'Review proposed work order'}</h2>
          </div>
          <span className="priority-pill">{workOrder.priority} priority</span>
        </div>
        <div className="work-order-preview">
          <div><span>Scope</span><strong>{workOrder.title}</strong></div>
          <div><span>Asset</span><strong>{workOrder.buildingId} · {workOrder.equipmentId}</strong></div>
          <p>{workOrder.description}</p>
        </div>
        {!decided ? (
          <div className="approval-actions">
            <button className="button button-primary" onClick={() => onDecision('approved')}><Check size={16} /> Approve work order</button>
            <button className="button button-secondary" onClick={() => onDecision('rejected')}><X size={16} /> Reject</button>
            <span><ShieldCheck size={14} /> No action is taken without your decision</span>
          </div>
        ) : (
          <div className="decision-message">
            {workOrder.status === 'approved'
              ? `Approval recorded. Work order ${workOrder.resultingId ?? ''} is now available.`
              : 'Rejection recorded. No work order was created.'}
            <span>Reset from Lab</span>
          </div>
        )}
      </div>
    </section>
  )
}
