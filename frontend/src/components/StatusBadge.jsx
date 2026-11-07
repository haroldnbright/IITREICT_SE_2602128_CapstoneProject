// Colored label for an order status
import { STATUS_LABELS } from '../utils/format'

// Shows the readable status name, styled by a CSS class per status
export default function StatusBadge({ status }) {
  return <span className={`badge badge-${status.toLowerCase()}`}>{STATUS_LABELS[status] || status}</span>
}
