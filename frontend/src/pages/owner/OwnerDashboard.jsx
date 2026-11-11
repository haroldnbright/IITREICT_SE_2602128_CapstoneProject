// Owner dashboard page, restaurant owner: open/close the restaurant, see reminders, stats and refund requests
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../../api/client'
import { Empty, ErrorBox, Loader } from '../../components/Feedback'
import OrderTicket from '../../components/OrderTicket'
import Pagination from '../../components/Pagination'
import { money, STATUS_LABELS, timeAgo } from '../../utils/format'
import useApi from '../../utils/useApi'

// Number of reminders on each page
const REMINDERS_PAGE_SIZE = 5
// Number of refund requests on each page
const RETURNS_PAGE_SIZE = 4

// Overview of the owner's restaurant, built from four separate API calls that load and fail independently
export default function OwnerDashboard() {
  const restaurant = useApi(() => api('/owner/restaurant'), [])
  const stats = useApi(() => api('/owner/stats'), [])
  // Reminders and refund requests each have their own page number
  const [reminderPage, setReminderPage] = useState(1)
  const reminders = useApi(
    () => api('/owner/reminders', { params: { page: reminderPage, size: REMINDERS_PAGE_SIZE } }),
    [reminderPage],
  )
  const [returnPage, setReturnPage] = useState(1)
  const returns = useApi(
    () => api('/owner/returns', { params: { page: returnPage, size: RETURNS_PAGE_SIZE } }),
    [returnPage],
  )
  const [busy, setBusy] = useState(false)
  const [actionError, setActionError] = useState('')

  // Opens or closes the restaurant for new orders
  const toggleOpen = async () => {
    setBusy(true)
    try {
      const body = { is_open: !restaurant.data.is_open }
      const updated = await api('/owner/restaurant', { method: 'PUT', body })
      // The API returns the updated restaurant, so use it directly instead of reloading
      restaurant.setData(updated)
    } catch (err) {
      setActionError(err.message)
    } finally {
      setBusy(false)
    }
  }

  // Approves or rejects a customer's refund request, with an optional note for the customer
  const decide = async (orderId, approve) => {
    let promptText = 'Why are you rejecting this? (optional)'
    if (approve) promptText = 'Note for the customer (optional)'
    const note = window.prompt(promptText)
    // null means the owner pressed Cancel on the prompt
    if (note === null) return
    setActionError('')
    try {
      await api(`/owner/orders/${orderId}/return-decision`, { method: 'POST', body: { approve, note } })
      // The request leaves the list, and an approved refund changes the refunded total
      returns.reload()
      stats.reload()
    } catch (err) {
      setActionError(err.message)
    }
  }

  // The header needs the restaurant, so wait for it; the other sections show their own states
  if (restaurant.loading) return <Loader />
  if (restaurant.error) return <ErrorBox message={restaurant.error} onRetry={restaurant.reload} />
  const isOpen = restaurant.data.is_open
  const numbers = stats.data

  return (
    <section>
      <div className="page-head">
        <div>
          <h1>{restaurant.data.name}</h1>
          <p className="muted">{restaurant.data.cuisine}</p>
        </div>
        <div className="row">
          <button className={isOpen ? 'btn btn-quiet' : 'btn btn-primary'} onClick={toggleOpen} disabled={busy}>
            {isOpen ? 'Stop taking orders' : 'Start taking orders'}
          </button>
          <Link to="/owner/orders" className="btn btn-primary">Manage orders</Link>
        </div>
      </div>
      <ErrorBox message={actionError} />

      {/* Reminders come first: they need action */}
      <div className="panel panel-alert">
        <div className="panel-head">
          <h2>Orders waiting too long</h2>
          <button className="btn btn-quiet btn-small" onClick={reminders.reload}>Refresh</button>
        </div>
        <ErrorBox message={reminders.error} />
        {reminders.data?.items.length === 0 && <p className="muted">Nothing waiting. Orders are moving on time.</p>}
        <ul className="reminder-list">
          {reminders.data?.items.map((reminder) => (
            <li key={reminder.id}>
              <span>{reminder.message}</span>
              <span className="muted small">flagged {timeAgo(reminder.created_at)}</span>
              {/* Opens the orders page already filtered to this order's status */}
              <Link to={`/owner/orders?status=${reminder.order_status}`} className="btn btn-quiet btn-small">Open</Link>
            </li>
          ))}
        </ul>
        {reminders.data && (
          <Pagination page={reminders.data.page} pages={reminders.data.pages} total={reminders.data.total} onChange={setReminderPage} />
        )}
      </div>

      <ErrorBox message={stats.error} onRetry={stats.reload} />
      {numbers && (
        <>
          <div className="stats">
            <div className="stat"><span>Orders today</span><strong>{numbers.orders_today}</strong></div>
            <div className="stat"><span>Active orders</span><strong>{numbers.active_orders}</strong></div>
            <div className="stat"><span>Delivered</span><strong>{numbers.delivered_orders}</strong></div>
            <div className="stat"><span>Revenue (delivered)</span><strong>{money(numbers.revenue)}</strong></div>
            <div className="stat"><span>Refunded</span><strong>{money(numbers.refunded_amount)}</strong></div>
            <div className="stat">
              <span>Rating</span>
              <strong>{numbers.avg_rating ? `★ ${numbers.avg_rating}` : 'None'}</strong>
              <small>{numbers.review_count} reviews</small>
            </div>
          </div>

          <div className="two-col">
            <div className="panel">
              <h2>Orders by status</h2>
              <ul className="bar-list">
                {Object.entries(numbers.status_counts).map(([status, count]) => {
                  // Bar width is this status's share of all orders
                  const barWidth = `${(count / numbers.total_orders) * 100}%`
                  return (
                    <li key={status}>
                      <span>{STATUS_LABELS[status]}</span>
                      <span className="bar"><span style={{ width: barWidth }} /></span>
                      <strong>{count}</strong>
                    </li>
                  )
                })}
              </ul>
            </div>
            <div className="panel">
              <h2>Best sellers</h2>
              {numbers.top_items.length === 0 ? (
                <p className="muted">No orders yet.</p>
              ) : (
                <ol className="top-list">
                  {numbers.top_items.map((item) => (
                    <li key={item.name}><span>{item.name}</span><strong>{item.quantity} sold</strong></li>
                  ))}
                </ol>
              )}
            </div>
          </div>
        </>
      )}

      <div className="panel">
        <h2>Refund requests</h2>
        <ErrorBox message={returns.error} onRetry={returns.reload} />
        {returns.loading && !returns.data && <Loader />}
        {returns.data?.items.length === 0 && <Empty title="No refund requests waiting" />}
        <div className="ticket-grid">
          {returns.data?.items.map((order) => (
            <OrderTicket key={order.id} order={order} heading={order.customer_name}>
              <button className="btn btn-primary btn-small" onClick={() => decide(order.id, true)}>Approve refund</button>
              <button className="btn btn-danger btn-small" onClick={() => decide(order.id, false)}>Reject</button>
            </OrderTicket>
          ))}
        </div>
        {returns.data && (
          <Pagination page={returns.data.page} pages={returns.data.pages} total={returns.data.total} onChange={setReturnPage} />
        )}
      </div>
    </section>
  )
}
