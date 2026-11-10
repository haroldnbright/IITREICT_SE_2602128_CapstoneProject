// Buttons a customer can use on their own order
import { useState } from 'react'
import { api } from '../api/client'
import { ReturnForm, ReviewForm } from './OrderForms'

// Cancel / review / refund buttons for one order. Each button only shows when the
// action is allowed, and the backend checks the same rules again.
// onUpdate(updatedOrder) is called so the parent page can show the new order state
export default function CustomerOrderActions({ order, onUpdate }) {
  const [form, setForm] = useState(null) // 'review' | 'return' | null
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  // Asks for confirmation, then cancels the order on the backend
  const cancel = async () => {
    if (!window.confirm(`Cancel order #${order.id}? The demo payment will be refunded.`)) return
    setBusy(true)
    setError('')
    try {
      const updatedOrder = await api(`/orders/${order.id}/cancel`, { method: 'POST' })
      onUpdate(updatedOrder)
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  // Closes the open form and passes the updated order up
  const done = (updated) => {
    setForm(null)
    onUpdate(updated)
  }

  // Which actions this order allows right now
  const canCancel = order.status === 'PLACED'
  const canReview = ['DELIVERED', 'REFUNDED'].includes(order.status) && !order.review
  const canReturn = order.status === 'DELIVERED' && order.return_status === 'none'

  // While a form is open it replaces the buttons
  if (form === 'review') return <ReviewForm orderId={order.id} onDone={done} onCancel={() => setForm(null)} />
  if (form === 'return') return <ReturnForm orderId={order.id} onDone={done} onCancel={() => setForm(null)} />

  return (
    <>
      {canCancel && <button className="btn btn-danger btn-small" disabled={busy} onClick={cancel}>Cancel order</button>}
      {canReview && <button className="btn btn-primary btn-small" onClick={() => setForm('review')}>Rate order</button>}
      {canReturn && <button className="btn btn-quiet btn-small" onClick={() => setForm('return')}>Request refund</button>}
      {error && <p className="form-error">{error}</p>}
    </>
  )
}
