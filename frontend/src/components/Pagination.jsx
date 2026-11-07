// Previous/next page controls for long lists

// Shows the current page and total, and calls onChange(newPage); hidden when there is only one page
export default function Pagination({ page, pages, total, onChange }) {
  if (!pages || pages <= 1) return null
  return (
    <div className="pagination">
      <button className="btn btn-quiet btn-small" disabled={page <= 1} onClick={() => onChange(page - 1)}>
        Previous
      </button>
      <span>
        Page {page} of {pages} ({total} total)
      </span>
      <button className="btn btn-quiet btn-small" disabled={page >= pages} onClick={() => onChange(page + 1)}>
        Next
      </button>
    </div>
  )
}
