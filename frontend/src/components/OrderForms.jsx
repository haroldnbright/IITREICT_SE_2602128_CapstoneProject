// Small inline forms for reviewing an order or asking for a refund
import { useState } from 'react'
import { api } from '../api/client'

// The star values a customer can pick, from 1 to 5
const STAR_VALUES = [1, 2, 3, 4, 5]
// Shortest refund reason the form accepts
const MIN_REASON_LENGTH = 5

// Star rating + comment. Calls onDone(updatedOrder) after saving.
export function ReviewForm({ orderId, onDone, onCancel }) {
  const [rating, setRating] = useState(5)
  const [comment, setComment] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  // Saves the review; on success the parent gets the updated order
  const submit = async (event) => {
    event.preventDefault()
    setSaving(true)
    setError('')
    try {
      const updatedOrder = await api(`/orders/${orderId}/review`, { method: 'POST', body: { rating, comment } })
      onDone(updatedOrder)
    } catch (err) {
      setError(err.message)
      // Only reset saving on error; on success the parent closes the form
      setSaving(false)
    }
  }

  return (
    <form className="inline-form" onSubmit={submit}>
      <div className="stars" role="radiogroup" aria-label="Rating">
        {/* Stars up to the chosen rating are lit ("on") */}
        {STAR_VALUES.map((stars) => (
          <button type="button" key={stars} role="radio" aria-checked={rating === stars} aria-label={`${stars} stars`}
            className={stars <= rating ? 'star on' : 'star'} onClick={() => setRating(stars)}>
            ★
          </button>
        ))}
      </div>
      <textarea rows="2" placeholder="What did you think? (optional)" value={comment} maxLength={1000}
        onChange={(e) => setComment(e.target.value)} />
      {error && <p className="form-error">{error}</p>}
      <div className="row">
        <button className="btn btn-primary btn-small" disabled={saving}>{saving ? 'Saving...' : 'Submit review'}</button>
        <button type="button" className="btn btn-quiet btn-small" onClick={onCancel}>Close</button>
      </div>
    </form>
  )
}

// Reason is required. Calls onDone(updatedOrder) after saving.
export function ReturnForm({ orderId, onDone, onCancel }) {
  const [reason, setReason] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  // Checks the reason length first, then sends the refund request
  const submit = async (event) => {
    event.preventDefault()
    if (reason.trim().length < MIN_REASON_LENGTH) {
      setError(`Tell us a bit more (at least ${MIN_REASON_LENGTH} characters).`)
      return
    }
    setSaving(true)
    setError('')
    try {
      const updatedOrder = await api(`/orders/${orderId}/return`, { method: 'POST', body: { reason } })
      onDone(updatedOrder)
    } catch (err) {
      setError(err.message)
      // Only reset saving on error; on success the parent closes the form
      setSaving(false)
    }
  }

  return (
    <form className="inline-form" onSubmit={submit}>
      <textarea rows="2" placeholder="Why do you want a return or refund?" value={reason} maxLength={1000}
        onChange={(e) => setReason(e.target.value)} required />
      {error && <p className="form-error">{error}</p>}
      <div className="row">
        <button className="btn btn-primary btn-small" disabled={saving}>{saving ? 'Sending...' : 'Request refund'}</button>
        <button type="button" className="btn btn-quiet btn-small" onClick={onCancel}>Close</button>
      </div>
    </form>
  )
}
