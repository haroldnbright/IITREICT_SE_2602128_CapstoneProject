// Order detail page, customer: tracking, items, payments and actions for one order
import { Link, useLocation, useParams } from 'react-router-dom'
import { api } from '../../api/client'
import CustomerOrderActions from '../../components/CustomerOrderActions'
import { ErrorBox, Loader } from '../../components/Feedback'
import StatusBadge from '../../components/StatusBadge'
import StatusTracker from '../../components/StatusTracker'
import { dateTime, money, PAYMENT_LABELS, RETURN_LABELS, timeAgo } from '../../utils/format'
import useApi from '../../utils/useApi'

// Full view of a single order with a manual Refresh button for tracking
export default function OrderDetail() {
  const { id } = useParams()
  const location = useLocation()
  const { data: order, setData, loading, error, reload } = useApi(() => api(`/orders/${id}`), [id])

  // Only block the page on first load; a failed refresh keeps showing the last known order
  if (loading && !order) return <Loader text="Loading order..." />
  if (error && !order) return <ErrorBox message={error} onRetry={reload} />

  return (
    <section className="narrow">
      <Link to="/orders" className="back-link">My orders</Link>
      {location.state?.justPlaced && <p className="success-box">Order placed. The restaurant will accept it shortly.</p>}

      <div className="page-head">
        <div>
          <h1>Order #{order.id}</h1>
          <p className="muted">{order.restaurant_name} | placed {dateTime(order.created_at)}</p>
        </div>
        <StatusBadge status={order.status} />
      </div>

      <div className="panel">
        <div className="panel-head">
          <h2>Tracking</h2>
          <button className="btn btn-quiet btn-small" onClick={reload} disabled={loading}>
            {loading ? 'Refreshing...' : 'Refresh'}
          </button>
        </div>
        <StatusTracker status={order.status} />
        <p className="muted small">Last update {timeAgo(order.status_updated_at)}</p>
        {order.delivery_partner_name && <p>Your rider: <strong>{order.delivery_partner_name}</strong></p>}
        <p>Delivering to: {order.delivery_address}</p>
      </div>

      <div className="panel">
        <h2>Items</h2>
        <ul className="ticket-items">
          {order.items.map((item) => (
            <li key={item.id}><span>{item.quantity} x {item.name}</span><span>{money(item.price * item.quantity)}</span></li>
          ))}
        </ul>
        <div className="ticket-total"><span>Total</span><strong>{money(order.total_amount)}</strong></div>
      </div>

      <div className="panel">
        <h2>Payment</h2>
        <p>Status: <strong>{PAYMENT_LABELS[order.payment_status]}</strong>
          {order.return_status !== 'none' && <> | {RETURN_LABELS[order.return_status]}</>}</p>
        <table className="table">
          <thead><tr><th>Type</th><th>Reference</th><th>Amount</th><th>When</th></tr></thead>
          <tbody>
            {/* Each row is either the original payment or a refund; refunds show a minus sign */}
            {order.payments.map((payment) => (
              <tr key={payment.id}>
                <td>{payment.entry_type === 'payment' ? 'Payment' : 'Refund'}</td>
                <td>{payment.reference}</td>
                <td>{payment.entry_type === 'refund' ? '-' : ''}{money(payment.amount)}</td>
                <td>{dateTime(payment.created_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {order.return_reason && <p className="muted">Your return reason: {order.return_reason}</p>}
        {order.return_note && <p className="muted">Restaurant's reply: {order.return_note}</p>}
      </div>

      {order.review && (
        <div className="panel">
          <h2>Your review</h2>
          <p><strong>{'★'.repeat(order.review.rating)}</strong> {order.review.comment}</p>
        </div>
      )}

      <div className="ticket-actions">
        {/* Actions (cancel, rate, request refund) hand back the updated order, which replaces the page data */}
        <CustomerOrderActions order={order} onUpdate={setData} />
      </div>
    </section>
  )
}
