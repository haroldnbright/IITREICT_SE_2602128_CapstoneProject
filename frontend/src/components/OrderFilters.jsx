// Filter bar for order lists
import { STATUS_LABELS } from '../utils/format'

// Filters with nothing selected, used by the "Clear filters" button
const NO_FILTERS = { status: '', from: '', to: '' }

// Status + date range filters, reused by the customer and owner order lists
// filters is { status, from, to } and onChange receives the whole new filters object
export default function OrderFilters({ filters, onChange, statuses = Object.keys(STATUS_LABELS), showDates = true }) {
  // Builds a change handler that copies the filters and updates one field, for example updateField('status')
  const updateField = (key) => (event) => onChange({ ...filters, [key]: event.target.value })
  // Only offer "Clear filters" when at least one filter is set
  const hasFilters = filters.status || filters.from || filters.to

  return (
    <div className="filters">
      <label>
        Status
        <select value={filters.status} onChange={updateField('status')}>
          <option value="">All</option>
          {statuses.map((status) => (
            <option key={status} value={status}>{STATUS_LABELS[status]}</option>
          ))}
        </select>
      </label>
      {showDates && (
        <>
          <label>
            From
            <input type="date" value={filters.from} onChange={updateField('from')} />
          </label>
          <label>
            To
            <input type="date" value={filters.to} min={filters.from} onChange={updateField('to')} />
          </label>
        </>
      )}
      {hasFilters && (
        <button className="btn btn-quiet btn-small" onClick={() => onChange({ ...NO_FILTERS })}>
          Clear filters
        </button>
      )}
    </div>
  )
}
