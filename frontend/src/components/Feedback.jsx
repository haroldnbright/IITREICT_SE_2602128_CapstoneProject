// Small shared pieces for loading, errors and empty lists

// Spinner with a short message while data is loading
export function Loader({ text = 'Loading...' }) {
  return (
    <div className="loader" role="status">
      <span className="spinner" aria-hidden="true" />
      {text}
    </div>
  )
}

// Error message with an optional "Try again" button; renders nothing when there is no message
export function ErrorBox({ message, onRetry }) {
  if (!message) return null
  return (
    <div className="error-box" role="alert">
      <span>{message}</span>
      {onRetry && <button className="btn btn-quiet btn-small" onClick={onRetry}>Try again</button>}
    </div>
  )
}

// Placeholder shown when a list has no items, with optional extra content as children
export function Empty({ title, children }) {
  return (
    <div className="empty">
      <p className="empty-title">{title}</p>
      {children}
    </div>
  )
}
