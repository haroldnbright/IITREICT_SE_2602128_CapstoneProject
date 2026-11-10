// My orders page, customer: lists the customer's orders with filters and per-order actions
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../../api/client'
import CustomerOrderActions from '../../components/CustomerOrderActions'
import { Empty, ErrorBox, Loader } from '../../components/Feedback'
import OrderFilters from '../../components/OrderFilters'
import OrderTicket from '../../components/OrderTicket'
import Pagination from '../../components/Pagination'
import { dateRangeParams } from '../../utils/format'
import useApi from '../../utils/useApi'

// Number of order tickets on each page
const PAGE_SIZE = 6

// Filterable, paginated grid of the customer's order tickets
export default function CustomerDashboard() {
  const [filters, setFilters] = useState({ status: '', from: '', to: '' })
  const [page, setPage] = useState(1)

  // Refetches whenever the filters or page change
  const { data, setData, loading, error, reload } = useApi(() => {
    // dateRangeParams converts the date inputs to UTC for the API
    const params = { status: filters.status, ...dateRangeParams(filters.from, filters.to), page, size: PAGE_SIZE }
    return api('/orders', { params })
  }, [filters, page])

  // Applies new filters and goes back to page 1 so the user doesn't land on an empty page
  const changeFilters = (newFilters) => {
    setFilters(newFilters)
    setPage(1)
  }

  // Swap the updated order into the list without reloading everything
  const replaceOrder = (updated) => {
    setData((current) => {
      const items = current.items.map((order) => (order.id === updated.id ? updated : order))
      return { ...current, items }
    })
  }

  // Pick what to show below the filters: a loader on first load, an empty message or the tickets
  let content = null
  if (loading && !data) {
    content = <Loader text="Loading orders..." />
  } else if (data && data.items.length === 0) {
    // Different message for "no matches" versus "no orders at all"
    const hasFilters = filters.status || filters.from || filters.to
    const emptyTitle = hasFilters ? 'No orders match these filters' : "You haven't ordered yet"
    content = (
      <Empty title={emptyTitle}>
        <Link to="/restaurants" className="btn btn-primary">Find something to eat</Link>
      </Empty>
    )
  } else if (data) {
    content = (
      <>
        <div className="ticket-grid">
          {data.items.map((order) => (
            <OrderTicket key={order.id} order={order} link={`/orders/${order.id}`}>
              <CustomerOrderActions order={order} onUpdate={replaceOrder} />
            </OrderTicket>
          ))}
        </div>
        <Pagination page={data.page} pages={data.pages} total={data.total} onChange={setPage} />
      </>
    )
  }

  return (
    <section>
      <div className="page-head">
        <h1>My orders</h1>
        <Link to="/insights" className="btn btn-quiet">Ask about my orders</Link>
      </div>
      <OrderFilters filters={filters} onChange={changeFilters} />
      <ErrorBox message={error} onRetry={reload} />
      {content}
    </section>
  )
}
