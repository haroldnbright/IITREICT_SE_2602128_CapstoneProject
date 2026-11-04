"""Customer order endpoints: place, list, view, cancel, review, request return.

GET /orders/{id} is also used by owners and delivery partners, but each user only
sees orders that belong to them.
"""
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import (
    MenuItem, Order, OrderItem, OrderStatus, PaymentLedger, PaymentStatus,
    Restaurant, ReturnStatus, Review, Role, User, utcnow,
)
from ..order_rules import check_transition
from ..schemas import OrderCreate, OrderOut, Page, ReturnIn, ReviewIn
from ..security import get_current_user, require_role
from ..services import (
    apply_order_filters, load_order, order_query, order_to_out, orders_page, record_refund, set_status, strip_or_none,
)

router = APIRouter(prefix="/orders", tags=["Customer orders"])

customer_only = require_role(Role.CUSTOMER)

# Most portions of one dish allowed in a single order
MAX_QUANTITY_PER_DISH = 20


def get_my_order(db: Session, order_id: int, customer: User) -> Order:
    """Load an order that belongs to this customer, or raise 404."""
    order = load_order(db, order_id)
    # Return 404 (not 403) so customers can't tell whether other people's order ids exist
    if order.customer_id != customer.id:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


def can_view_order(user: User, order: Order) -> bool:
    """True if this user is the order's customer, its restaurant's owner, or its delivery partner."""
    if user.role == Role.CUSTOMER:
        return order.customer_id == user.id
    if user.role == Role.OWNER:
        return order.restaurant.owner_id == user.id
    if user.role == Role.DELIVERY:
        return order.delivery_partner_id == user.id
    return False


@router.post("", response_model=OrderOut, status_code=status.HTTP_201_CREATED)
def place_order(data: OrderCreate, user: User = Depends(customer_only), db: Session = Depends(get_db)):
    """Place an order from one restaurant and record a mock payment for it."""
    restaurant = db.get(Restaurant, data.restaurant_id)
    if restaurant is None:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    if not restaurant.is_open:
        raise HTTPException(status_code=400, detail="This restaurant isn't taking orders right now")

    # Merge duplicate lines, e.g. two rows of the same dish
    quantities: dict[int, int] = {}
    for line in data.items:
        quantities[line.menu_item_id] = quantities.get(line.menu_item_id, 0) + line.quantity

    # Load all requested dishes in one query instead of one per line
    dishes = db.scalars(select(MenuItem).where(MenuItem.id.in_(quantities.keys()))).all()
    dishes_by_id = {dish.id: dish for dish in dishes}

    order = Order(
        customer_id=user.id,
        restaurant_id=restaurant.id,
        delivery_address=data.delivery_address.strip(),
        status=OrderStatus.PLACED,
        total_amount=0,
    )
    total = 0.0
    for dish_id, quantity in quantities.items():
        dish = dishes_by_id.get(dish_id)
        # Reject dishes that don't exist or belong to a different restaurant
        if dish is None or dish.restaurant_id != restaurant.id:
            raise HTTPException(status_code=400, detail=f"Dish {dish_id} is not on this restaurant's menu")
        if not dish.is_available:
            raise HTTPException(status_code=400, detail=f"{dish.name} is not available right now")
        # Re-checked after merging, since duplicate lines can add up past the per-line limit
        if quantity > MAX_QUANTITY_PER_DISH:
            raise HTTPException(status_code=400, detail=f"You can order at most {MAX_QUANTITY_PER_DISH} of one dish")
        # Price always comes from the database, never from the browser
        order.items.append(OrderItem(menu_item_id=dish.id, name=dish.name, price=dish.price, quantity=quantity))
        total += dish.price * quantity

    order.total_amount = round(total, 2)
    db.add(order)
    db.flush()  # gives order.id for the ledger row

    # Dummy payment: no real gateway, just a ledger row and the mock_paid status
    db.add(
        PaymentLedger(
            order_id=order.id,
            entry_type="payment",
            amount=order.total_amount,
            status=PaymentStatus.MOCK_PAID,
            reference=f"MOCKPAY-{uuid.uuid4().hex[:10].upper()}",
            note="Dummy payment, no money was charged",
        )
    )
    order.payment_status = PaymentStatus.MOCK_PAID
    db.commit()
    return order_to_out(load_order(db, order.id))


@router.get("", response_model=Page[OrderOut])
def my_orders(
    status: str | None = Query(None),
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=50),
    user: User = Depends(customer_only),
    db: Session = Depends(get_db),
):
    """List the customer's own orders, newest first, with optional filters."""
    query = order_query().where(Order.customer_id == user.id)
    return orders_page(db, apply_order_filters(query, status, date_from, date_to), page, size)


@router.get("/{order_id}", response_model=OrderOut)
def order_detail(order_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Show one order to its customer, its restaurant's owner, or its assigned delivery partner."""
    order = load_order(db, order_id)
    if not can_view_order(user, order):  # 404 so outsiders can't confirm the order exists
        raise HTTPException(status_code=404, detail="Order not found")
    return order_to_out(order)


@router.post("/{order_id}/cancel", response_model=OrderOut)
def cancel_order(order_id: int, user: User = Depends(customer_only), db: Session = Depends(get_db)):
    """Cancel an order that the restaurant hasn't accepted yet. Refunds the mock payment."""
    order = get_my_order(db, order_id, user)
    if order.status != OrderStatus.PLACED:
        raise HTTPException(status_code=400, detail="Orders can only be cancelled before the restaurant accepts them")
    check_transition(Role.CUSTOMER, order.status, OrderStatus.CANCELLED)
    set_status(order, OrderStatus.CANCELLED)
    record_refund(db, order, "Order cancelled by customer")
    db.commit()
    return order_to_out(load_order(db, order.id))


@router.post("/{order_id}/review", response_model=OrderOut, status_code=status.HTTP_201_CREATED)
def review_order(order_id: int, data: ReviewIn, user: User = Depends(customer_only), db: Session = Depends(get_db)):
    """Leave a rating and comment on a delivered order. Only one review per order."""
    order = get_my_order(db, order_id, user)
    if order.status not in (OrderStatus.DELIVERED, OrderStatus.REFUNDED):
        raise HTTPException(status_code=400, detail="You can review an order after it's delivered")
    if order.review is not None:
        raise HTTPException(status_code=409, detail="You've already reviewed this order")

    review = Review(
        order_id=order.id,
        customer_id=user.id,
        restaurant_id=order.restaurant_id,
        rating=data.rating,
        # Blank or whitespace-only comments are stored as NULL
        comment=strip_or_none(data.comment),
    )
    db.add(review)
    try:
        db.commit()
    except IntegrityError:  # two requests at once; the unique constraint catches it
        db.rollback()
        raise HTTPException(status_code=409, detail="You've already reviewed this order")
    db.expire_all()  # drop cached objects so the new review is loaded below
    return order_to_out(load_order(db, order.id))


@router.post("/{order_id}/return", response_model=OrderOut)
def request_return(order_id: int, data: ReturnIn, user: User = Depends(customer_only), db: Session = Depends(get_db)):
    """Ask for a return on a delivered order. The owner approves or rejects it later."""
    order = get_my_order(db, order_id, user)
    if order.return_status != ReturnStatus.NONE:
        raise HTTPException(status_code=409, detail="A return request already exists for this order")
    if order.status != OrderStatus.DELIVERED:
        raise HTTPException(status_code=400, detail="You can request a return only after the order is delivered")

    order.return_status = ReturnStatus.REQUESTED
    order.return_reason = data.reason.strip()
    order.return_requested_at = utcnow()
    db.commit()
    return order_to_out(load_order(db, order.id))
