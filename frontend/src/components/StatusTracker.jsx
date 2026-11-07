// Progress display for an order's delivery steps
import { ORDER_FLOW, STATUS_LABELS } from '../utils/format'

// Step line showing how far the order has moved through the lifecycle
export default function StatusTracker({ status }) {
  if (status === 'CANCELLED') return <p className="tracker-stopped">This order was cancelled.</p>
  // Position of the order's status in the flow
  // A refunded order was delivered first, so show every step as reached
  let currentIndex = ORDER_FLOW.indexOf(status)
  if (status === 'REFUNDED') currentIndex = ORDER_FLOW.length - 1

  // Steps before the current one are done, the current one is highlighted, later ones are plain
  const stepClass = (index) => {
    if (index < currentIndex) return 'done'
    if (index === currentIndex) return 'current'
    return ''
  }

  return (
    <ol className="tracker">
      {ORDER_FLOW.map((step, index) => (
        <li key={step} className={stepClass(index)}>
          <span className="tracker-dot" aria-hidden="true" />
          <span className="tracker-label">{STATUS_LABELS[step]}</span>
        </li>
      ))}
    </ol>
  )
}
