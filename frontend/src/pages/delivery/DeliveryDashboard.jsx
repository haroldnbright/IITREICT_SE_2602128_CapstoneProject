// Delivery dashboard page, delivery partner: see assigned orders and update their delivery status
import { useState } from 'react'
import { api } from '../../api/client'
import { Empty, ErrorBox, Loader } from '../../components/Feedback'
import OrderTicket from '../../components/OrderTicket'
import Pagination from '../../components/Pagination'
import { STATUS_LABELS } from '../../utils/format'
import useApi from '../../utils/useApi'

// The two tabs, each with the statuses offered in its status filter
const TABS = [
  { key: 'active', label: 'Current', statuses: ['ASSIGNED', 'OUT_FOR_DELIVERY'] },
  { key: 'history', label: 'History', statuses: ['DELIVERED', 'REFUNDED'] },
]

// The next step the rider can take from each status
const NEXT_STEP = {
  ASSIGNED: { status: 'OUT_FOR_DELIVERY', label: 'Picked up, out for delivery' },
  OUT_FOR_DELIVERY: { status: 'DELIVERED', label: 'Mark delivered' },
}

// Number of order tickets on each page
const PAGE_SIZE = 6

// Tabbed, paginated list of the rider's deliveries with a status button on each ticket
export default function DeliveryDashboard() {
  const [tab, setTab] = useState('active')
  const [status, setStatus] = useState('')
  const [page, setPage] = useState(1)
  // Id of the order being updated, so only its button is disabled
  const [busyId, setBusyId] = useState(null)
  const [actionError, setActionError] = useState('')

  // The API's scope param picks current or past orders; refetches when tab, status or page change
  const { data, setData, loading, error, reload } = useApi(
    () => api('/delivery/orders', { params: { scope: tab, status, page, size: PAGE_SIZE } }),
    [tab, status, page],
  )

  // Switches tab and resets the status filter and page, since they belong to the old tab
  const switchTab = (key) => {
    setTab(key)
    setStatus('')
    setPage(1)
  }

  // Changing the status filter starts again from page 1
  const changeStatus = (newStatus) => {
    setStatus(newStatus)
    setPage(1)
  }

  // Moves the order to its next delivery status (picked up, then delivered)
  const advance = async (order) => {
    setBusyId(order.id)
    setActionError('')
    try {
      const body = { status: NEXT_STEP[order.status].status }
      const updated = await api(`/delivery/orders/${order.id}/status`, { method: 'PATCH', body })
      // Delivered orders move to History, so drop them from the current list;
      // otherwise swap the updated order into the list
      const removeFromList = updated.status === 'DELIVERED' && tab === 'active'
      setData((current) => {
        let items
        if (removeFromList) {
          items = current.items.filter((item) => item.id !== updated.id)
        } else {
          items = current.items.map((item) => (item.id === updated.id ? updated : item))
        }
        return { ...current, items }
      })
    } catch (err) {
      setActionError(`Order #${order.id}: ${err.message}`)
    } finally {
      setBusyId(null)
    }
  }

  // Used to fill the status dropdown with only this tab's statuses
  const currentTab = TABS.find((tabInfo) => tabInfo.key === tab)

  // Pick what to show below the tabs: a loader on first load, an empty message or the tickets
  let content = null
  if (loading && !data) {
    content = <Loader text="Loading deliveries..." />
  } else if (data && data.items.length === 0) {
    const emptyTitle = tab === 'active' ? 'No deliveries assigned to you right now' : 'No completed deliveries yet'
    content = <Empty title={emptyTitle} />
  } else if (data) {
    content = (
      <>
        <div className="ticket-grid">
          {data.items.map((order) => (
            <OrderTicket key={order.id} order={order} showCustomer>
              {NEXT_STEP[order.status] && (
                <button className="btn btn-primary btn-small" disabled={busyId === order.id} onClick={() => advance(order)}>
                  {NEXT_STEP[order.status].label}
                </button>
              )}
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
        <h1>My deliveries</h1>
        <button className="btn btn-quiet" onClick={reload}>Refresh</button>
      </div>

      <div className="tabs" role="tablist">
        {TABS.map((tabInfo) => (
          <button key={tabInfo.key} role="tab" aria-selected={tab === tabInfo.key}
            className={tab === tabInfo.key ? 'tab active' : 'tab'} onClick={() => switchTab(tabInfo.key)}>
            {tabInfo.label}
          </button>
        ))}
        <label className="tab-filter">
          Status
          <select value={status} onChange={(e) => changeStatus(e.target.value)}>
            <option value="">All</option>
            {currentTab.statuses.map((statusOption) => (
              <option key={statusOption} value={statusOption}>{STATUS_LABELS[statusOption]}</option>
            ))}
          </select>
        </label>
      </div>

      <ErrorBox message={actionError} />
      <ErrorBox message={error} onRetry={reload} />
      {content}
    </section>
  )
}
