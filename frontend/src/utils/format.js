// Formatting helpers used across pages

// Milliseconds in one minute, for turning time differences into minutes
const MS_PER_MINUTE = 60 * 1000

// How dates are shown, for example "5 Nov, 2:30 pm"
const DATE_TIME_OPTIONS = { day: 'numeric', month: 'short', hour: 'numeric', minute: '2-digit' }

// Formats an amount as Indian rupees, treating missing values as 0
export const money = (amount) => {
  const number = Number(amount || 0)
  const formatted = number.toLocaleString('en-IN', { maximumFractionDigits: 2 })
  return `₹${formatted}`
}

// The backend stores UTC times without a "Z", so add it before parsing
export const parseDate = (value) => {
  if (value.endsWith('Z')) return new Date(value)
  return new Date(`${value}Z`)
}

// Short local date and time for display, or an empty string if there is no date
export const dateTime = (value) => {
  if (!value) return ''
  return parseDate(value).toLocaleString('en-IN', DATE_TIME_OPTIONS)
}

// Relative time like "5 min ago" for recent activity
export const timeAgo = (value) => {
  const msAgo = Date.now() - parseDate(value).getTime()
  const minutes = Math.round(msAgo / MS_PER_MINUTE)
  if (minutes < 1) return 'just now'
  if (minutes < 60) return `${minutes} min ago`
  const hours = Math.round(minutes / 60)
  if (hours < 24) return `${hours} h ago`
  const days = Math.round(hours / 24)
  return `${days} d ago`
}

// Turn the date inputs (local days) into UTC timestamps for the API
// "from" starts at the beginning of its day and "to" ends at the very end of its day
// A missing date stays undefined so the API client leaves it out
export const dateRangeParams = (from, to) => {
  let dateFrom
  let dateTo
  if (from) dateFrom = new Date(`${from}T00:00:00`).toISOString()
  if (to) dateTo = new Date(`${to}T23:59:59.999`).toISOString()
  return { date_from: dateFrom, date_to: dateTo }
}

// Human-friendly names for each order status sent by the backend
export const STATUS_LABELS = {
  PLACED: 'Placed',
  ACCEPTED: 'Accepted',
  PREPARING: 'Preparing',
  READY: 'Ready',
  ASSIGNED: 'Rider assigned',
  OUT_FOR_DELIVERY: 'Out for delivery',
  DELIVERED: 'Delivered',
  CANCELLED: 'Cancelled',
  REFUNDED: 'Refunded',
}

// Normal order lifecycle in order, used by the status tracker
export const ORDER_FLOW = ['PLACED', 'ACCEPTED', 'PREPARING', 'READY', 'ASSIGNED', 'OUT_FOR_DELIVERY', 'DELIVERED']

// Display text for payment and return states shown on order tickets
export const PAYMENT_LABELS = { pending: 'Payment pending', mock_paid: 'Paid (demo)', refunded: 'Refunded' }
export const RETURN_LABELS = { none: '', requested: 'Return requested', approved: 'Return approved', rejected: 'Return rejected' }
