// Orders page, restaurant owner: move orders through the kitchen steps and assign riders
import { useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { api } from '../../api/client'
import { Empty, ErrorBox, Loader } from '../../components/Feedback'
import OrderFilters from '../../components/OrderFilters'
import OrderTicket from '../../components/OrderTicket'
import Pagination from '../../components/Pagination'
import { dateRangeParams, STATUS_LABELS } from '../../utils/format'
import useApi from '../../utils/useApi'

// The next step the owner can take from each status
const NEXT_STEP = {
  PLACED: { status: 'ACCEPTED', label: 'Accept order' },
  ACCEPTED: { status: 'PREPARING', label: 'Start preparing' },
  PREPARING: { status: 'READY', label: 'Mark ready' },
}
// Statuses where a rider has the order, so the ticket shows who has it
const WITH_RIDER_STATUSES = ['ASSIGNED', 'OUT_FOR_DELIVERY']
// Number of order tickets on each page
const PAGE_SIZE = 8

// Filterable, paginated list of the restaurant's orders with an action button on each ticket
export default function OwnerOrders() {
  const [searchParams] = useSearchParams()
  // A ?status= link (e.g. from a dashboard reminder) sets the starting status filter
  const [filters, setFilters] = useState({ status: searchParams.get('status') || '', from: '', to: '' })
  const [page, setPage] = useState(1)
  const [partnerChoice, setPartnerChoice] = useState({}) // orderId -> partnerId
  // Id of the order whose action is running, so only its buttons are disabled
  const [busyId, setBusyId] = useState(null)
  const [actionError, setActionError] = useState('')

  // Refetches whenever the filters or page change
  const orders = useApi(() => {
    // dateRangeParams converts the date inputs to UTC for the API
    const params = { status: filters.status, ...dateRangeParams(filters.from, filters.to), page, size: PAGE_SIZE }
    return api('/owner/orders', { params })
  }, [filters, page])
  // Riders to choose from, each with their count of active orders
  const partners = useApi(() => api('/owner/delivery-partners'), [])

  // New filters always start again from page 1
  const changeFilters = (newFilters) => {
    setFilters(newFilters)
    setPage(1)
  }

  // Remembers which rider the owner picked in one order's dropdown
  const choosePartner = (orderId, partnerId) => {
    setPartnerChoice({ ...partnerChoice, [orderId]: partnerId })
  }

  // Swaps the updated order into the list without reloading everything
  const replaceOrder = (updated) => {
    orders.setData((current) => {
      const items = current.items.map((order) => (order.id === updated.id ? updated : order))
      return { ...current, items }
    })
  }

  // Shared wrapper for order actions: marks the order busy, runs the request and shows any error.
  // request is a function that calls the API and returns the updated order.
  const run = async (orderId, request) => {
    setBusyId(orderId)
    setActionError('')
    try {
      const updated = await request()
      replaceOrder(updated)
    } catch (err) {
      setActionError(`Order #${orderId}: ${err.message}`)
    } finally {
      setBusyId(null)
    }
  }

  // Moves the order to its next kitchen status (accept, preparing, ready)
  const advance = (order) => {
    const body = { status: NEXT_STEP[order.status].status }
    run(order.id, () => api(`/owner/orders/${order.id}/status`, { method: 'PATCH', body }))
  }

  // Assigns a ready order to the chosen delivery partner
  const assign = (order) => {
    let partnerId = partnerChoice[order.id]
    // If the owner never touched the dropdown, use the first rider it shows
    if (!partnerId && partners.data && partners.data.length > 0) {
      partnerId = partners.data[0].id
    }
    if (!partnerId) {
      setActionError('There are no delivery partners yet.')
      return
    }
    run(order.id, async () => {
      const body = { delivery_partner_id: Number(partnerId) }
      const updated = await api(`/owner/orders/${order.id}/assign`, { method: 'POST', body })
      partners.reload() // their active order counts changed
      return updated
    })
  }

  // Pick what to show below the filters: a loader on first load, an empty message or the tickets
  let content = null
  if (orders.loading && !orders.data) {
    content = <Loader text="Loading orders..." />
  } else if (orders.data && orders.data.items.length === 0) {
    content = <Empty title="No orders match these filters" />
  } else if (orders.data) {
    content = (
      <>
        <div className="ticket-grid">
          {orders.data.items.map((order) => {
            const nextStep = NEXT_STEP[order.status]
            const isBusy = busyId === order.id
            return (
              <OrderTicket key={order.id} order={order} heading={order.customer_name}>
                {/* Kitchen step button, for orders that are not ready yet */}
                {nextStep && (
                  <button className="btn btn-primary btn-small" disabled={isBusy} onClick={() => advance(order)}>
                    {nextStep.label}
                  </button>
                )}
                {/* Rider picker, for orders that are ready to go */}
                {order.status === 'READY' && (
                  <div className="assign">
                    <select aria-label="Delivery partner" value={partnerChoice[order.id] || ''}
                      onChange={(e) => choosePartner(order.id, e.target.value)}>
                      {(partners.data || []).map((partner) => (
                        <option key={partner.id} value={partner.id}>{partner.name} ({partner.active_orders} active)</option>
                      ))}
                    </select>
                    <button className="btn btn-primary btn-small" disabled={isBusy} onClick={() => assign(order)}>
                      Assign rider
                    </button>
                  </div>
                )}
                {/* Who has the order once it has left the kitchen */}
                {WITH_RIDER_STATUSES.includes(order.status) && (
                  <span className="muted small">{STATUS_LABELS[order.status]} with {order.delivery_partner_name}</span>
                )}
              </OrderTicket>
            )
          })}
        </div>
        <Pagination page={orders.data.page} pages={orders.data.pages} total={orders.data.total} onChange={setPage} />
      </>
    )
  }

  return (
    <section>
      <div className="page-head">
        <h1>Orders</h1>
        <button className="btn btn-quiet" onClick={orders.reload}>Refresh</button>
      </div>
      <OrderFilters filters={filters} onChange={changeFilters} />
      <ErrorBox message={actionError} />
      <ErrorBox message={orders.error} onRetry={orders.reload} />
      {content}
    </section>
  )
}
