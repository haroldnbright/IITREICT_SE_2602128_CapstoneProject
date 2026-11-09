// Card that shows the details of one order
import { Link } from 'react-router-dom'
import StatusBadge from './StatusBadge'
import { dateTime, money, PAYMENT_LABELS, RETURN_LABELS } from '../utils/format'

// An order shown as a kitchen ticket. Pages pass their own action buttons as children.
// heading overrides the restaurant name, link adds a "Track order" button, showCustomer shows contact details for staff
export default function OrderTicket({ order, heading, link, showCustomer = false, children }) {
  // Staff see the customer's details instead, so the rider line is only for customers
  const showRider = order.delivery_partner_name && !showCustomer
  // The actions row only appears when there is something to put in it
  const hasActions = children || link

  return (
    <article className="ticket">
      <div className="ticket-head">
        <div>
          <p className="ticket-number">#{order.id}</p>
          <p className="ticket-sub">{heading ?? order.restaurant_name} | {dateTime(order.created_at)}</p>
        </div>
        <StatusBadge status={order.status} />
      </div>

      <ul className="ticket-items">
        {order.items.map((item) => (
          <li key={item.id}>
            <span>{item.quantity} x {item.name}</span>
            <span>{money(item.price * item.quantity)}</span>
          </li>
        ))}
      </ul>

      <div className="ticket-total">
        <span>Total</span>
        <strong>{money(order.total_amount)}</strong>
      </div>

      <div className="ticket-meta">
        <span className={`pill pill-${order.payment_status}`}>{PAYMENT_LABELS[order.payment_status]}</span>
        {order.return_status !== 'none' && (
          <span className={`pill pill-return-${order.return_status}`}>{RETURN_LABELS[order.return_status]}</span>
        )}
        {order.review && <span className="pill">Rated {order.review.rating}/5</span>}
      </div>

      {showCustomer && (
        <div className="ticket-customer">
          <p><strong>{order.customer_name}</strong>{order.customer_phone && <> | <a href={`tel:${order.customer_phone}`}>{order.customer_phone}</a></>}</p>
          <p>{order.delivery_address}</p>
        </div>
      )}
      {showRider && <p className="ticket-note">Rider: {order.delivery_partner_name}</p>}
      {order.return_reason && <p className="ticket-note">Return reason: {order.return_reason}</p>}
      {order.return_note && <p className="ticket-note">Restaurant note: {order.return_note}</p>}

      {hasActions && (
        <div className="ticket-actions">
          {children}
          {link && <Link to={link} className="btn btn-quiet btn-small">Track order</Link>}
        </div>
      )}
    </article>
  )
}
