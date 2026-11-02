"""Small helpers shared by several routers."""
import math
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from . import schemas
from .models import Order, PaymentLedger, PaymentStatus, Restaurant, Review, User, utcnow


def paginate(db: Session, query, page: int, size: int) -> tuple[list, int, int]:
    """Run a select() with LIMIT/OFFSET. Returns (rows, total, pages)."""
    # Count over a subquery with ORDER BY stripped, since ordering is irrelevant to the total
    total = db.scalar(select(func.count()).select_from(query.order_by(None).subquery()))
    rows = db.scalars(query.offset((page - 1) * size).limit(size)).all()
    # Round up, so 11 rows at 10 per page is 2 pages
    pages = math.ceil(total / size) if total else 0
    return rows, total, pages


def to_utc(value: datetime | None) -> datetime | None:
    """Convert a datetime from a query string to naive UTC (how we store times)."""
    if value is None:
        return None
    if value.tzinfo is not None:
        value = value.astimezone(timezone.utc).replace(tzinfo=None)
    return value


def order_query():
    """Base query for orders with everything the response needs loaded up front."""
    return select(Order).options(
        selectinload(Order.items),
        selectinload(Order.restaurant),
        selectinload(Order.customer),
        selectinload(Order.delivery_partner),
        selectinload(Order.review).selectinload(Review.customer),
        selectinload(Order.payments),
    )


def apply_order_filters(query, status: str | None, date_from: datetime | None, date_to: datetime | None):
    """Add optional status and date-range filters, newest orders first."""
    if status:
        query = query.where(Order.status == status.upper())
    if date_from:
        query = query.where(Order.created_at >= to_utc(date_from))
    if date_to:
        query = query.where(Order.created_at <= to_utc(date_to))
    # Order.id breaks ties so pagination stays stable when timestamps match
    return query.order_by(Order.created_at.desc(), Order.id.desc())


def review_to_out(review: Review) -> schemas.ReviewOut:
    """Convert a Review row to its API schema, adding the reviewer's name."""
    return schemas.ReviewOut(
        id=review.id,
        order_id=review.order_id,
        rating=review.rating,
        comment=review.comment,
        created_at=review.created_at,
        customer_name=review.customer.name if review.customer else None,
    )


def strip_or_none(text: str | None) -> str | None:
    """Trim spaces from optional text; blank or whitespace-only text becomes None."""
    if text is None:
        return None
    text = text.strip()
    if text == "":
        return None
    return text


def order_to_out(order: Order) -> schemas.OrderOut:
    """Flatten an Order and its related rows into the OrderOut response schema."""
    if order.delivery_partner:
        delivery_partner_name = order.delivery_partner.name
    else:
        delivery_partner_name = None

    if order.review:
        review = review_to_out(order.review)
    else:
        review = None

    items = []
    for item in order.items:
        items.append(schemas.OrderItemOut.model_validate(item))

    # Oldest ledger entry first, so the payment comes before any refund
    payments = []
    for payment in sorted(order.payments, key=lambda payment: payment.id):
        payments.append(schemas.PaymentOut.model_validate(payment))

    return schemas.OrderOut(
        id=order.id,
        status=order.status,
        total_amount=order.total_amount,
        delivery_address=order.delivery_address,
        payment_status=order.payment_status,
        return_status=order.return_status,
        return_reason=order.return_reason,
        return_note=order.return_note,
        created_at=order.created_at,
        status_updated_at=order.status_updated_at,
        restaurant_id=order.restaurant_id,
        restaurant_name=order.restaurant.name,
        customer_name=order.customer.name,
        customer_phone=order.customer.phone,
        delivery_partner_id=order.delivery_partner_id,
        delivery_partner_name=delivery_partner_name,
        items=items,
        review=review,
        payments=payments,
    )


def orders_page(db: Session, query, page: int, size: int) -> schemas.Page[schemas.OrderOut]:
    """Paginate an order query and wrap the results in a Page response."""
    rows, total, pages = paginate(db, query, page, size)
    items = [order_to_out(order) for order in rows]
    return schemas.Page[schemas.OrderOut](items=items, total=total, page=page, size=size, pages=pages)


def load_order(db: Session, order_id: int) -> Order:
    """Fetch one order with its relations loaded. Raises 404 if it doesn't exist."""
    order = db.scalars(order_query().where(Order.id == order_id)).first()
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


def get_owner_restaurant(db: Session, owner: User) -> Restaurant:
    """Return the restaurant owned by this user. Raises 404 if they don't have one."""
    restaurant = db.scalars(select(Restaurant).where(Restaurant.owner_id == owner.id)).first()
    if restaurant is None:
        raise HTTPException(status_code=404, detail="You don't have a restaurant yet")
    return restaurant


def set_status(order: Order, new_status: str) -> None:
    """Change an order's status and stamp when it changed (used by the reminder job)."""
    order.status = new_status
    order.status_updated_at = utcnow()


def record_refund(db: Session, order: Order, note: str) -> None:
    """Write a refund row in the payment ledger and mark the order's payment as refunded."""
    db.add(
        PaymentLedger(
            order_id=order.id,
            entry_type="refund",
            amount=order.total_amount,
            status=PaymentStatus.REFUNDED,
            # Payments are simulated, so the reference is just a random mock id
            reference=f"MOCKREF-{uuid.uuid4().hex[:10].upper()}",
            note=note,
        )
    )
    order.payment_status = PaymentStatus.REFUNDED



