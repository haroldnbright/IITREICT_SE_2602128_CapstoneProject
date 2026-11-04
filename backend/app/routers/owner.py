"""Restaurant owner endpoints. Every route here requires the "owner" role, and every
query is limited to the owner's own restaurant."""
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy import func, select, text, update
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import (
    MenuItem, Order, OrderItem, OrderStatus, PaymentLedger, ReminderLog,
    ReturnStatus, Review, Role, User, utcnow,
)
from ..order_rules import check_transition
from ..reminders import create_reminders
from ..schemas import (
    AssignIn, AvailabilityIn, DeliveryPartnerOut, MenuItemIn, MenuItemOut, MenuItemUpdate, Message,
    OrderOut, Page, ReminderOut, RestaurantOut, RestaurantUpdate, ReturnDecisionIn, StatsOut, StatusUpdate, TopItem,
)
from ..security import require_role
from ..services import (
    apply_order_filters, get_owner_restaurant, load_order, order_query, order_to_out,
    orders_page, paginate, record_refund, set_status, strip_or_none,
)

router = APIRouter(prefix="/owner", tags=["Restaurant owner"])

owner_only = require_role(Role.OWNER)

# Orders that are neither finished nor cancelled, for the "active orders" stat
ACTIVE_STATUSES = [OrderStatus.PLACED, OrderStatus.ACCEPTED, OrderStatus.PREPARING,
                   OrderStatus.READY, OrderStatus.ASSIGNED, OrderStatus.OUT_FOR_DELIVERY]

# Orders a delivery partner is currently busy with
ON_DELIVERY_STATUSES = [OrderStatus.ASSIGNED, OrderStatus.OUT_FOR_DELIVERY]


def get_restaurant_order(db: Session, order_id: int, owner: User) -> Order:
    """Load an order placed at this owner's restaurant, or raise 404."""
    order = load_order(db, order_id)
    # 404 rather than 403 so owners can't probe other restaurants' orders
    if order.restaurant.owner_id != owner.id:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


def get_restaurant_dish(db: Session, item_id: int, owner: User) -> MenuItem:
    """Load a dish from this owner's menu, or raise 404."""
    restaurant = get_owner_restaurant(db, owner)
    dish = db.get(MenuItem, item_id)
    if dish is None or dish.restaurant_id != restaurant.id:
        raise HTTPException(status_code=404, detail="Dish not found")
    return dish


# ---------- Restaurant profile ----------
@router.get("/restaurant", response_model=RestaurantOut)
def my_restaurant(user: User = Depends(owner_only), db: Session = Depends(get_db)):
    """Show the owner's restaurant profile (without ratings)."""
    restaurant = get_owner_restaurant(db, user)
    return RestaurantOut(id=restaurant.id, name=restaurant.name, description=restaurant.description,
                         cuisine=restaurant.cuisine, address=restaurant.address, is_open=restaurant.is_open)


@router.put("/restaurant", response_model=RestaurantOut)
def update_restaurant(data: RestaurantUpdate, user: User = Depends(owner_only), db: Session = Depends(get_db)):
    """Update the owner's restaurant profile, including opening or closing it."""
    restaurant = get_owner_restaurant(db, user)
    # exclude_unset: only fields the client actually sent are changed
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(restaurant, field, value)
    db.commit()
    return RestaurantOut(id=restaurant.id, name=restaurant.name, description=restaurant.description,
                         cuisine=restaurant.cuisine, address=restaurant.address, is_open=restaurant.is_open)


# ---------- Menu management ----------
@router.get("/menu", response_model=list[MenuItemOut])
def my_menu(user: User = Depends(owner_only), db: Session = Depends(get_db)):
    """List every dish on the owner's menu, including unavailable ones."""
    restaurant = get_owner_restaurant(db, user)
    return db.scalars(
        select(MenuItem).where(MenuItem.restaurant_id == restaurant.id).order_by(MenuItem.category, MenuItem.name)
    ).all()


@router.post("/menu", response_model=MenuItemOut, status_code=status.HTTP_201_CREATED)
def add_dish(data: MenuItemIn, user: User = Depends(owner_only), db: Session = Depends(get_db)):
    """Add a dish to the owner's menu."""
    restaurant = get_owner_restaurant(db, user)
    dish = MenuItem(restaurant_id=restaurant.id, **data.model_dump())
    db.add(dish)
    db.commit()
    db.refresh(dish)
    return dish


@router.put("/menu/{item_id}", response_model=MenuItemOut)
def update_dish(item_id: int, data: MenuItemUpdate, user: User = Depends(owner_only), db: Session = Depends(get_db)):
    """Edit a dish; only fields the client sent are changed."""
    dish = get_restaurant_dish(db, item_id, user)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(dish, field, value)
    db.commit()
    db.refresh(dish)
    return dish


@router.patch("/menu/{item_id}/availability", response_model=MenuItemOut)
def set_availability(item_id: int, data: AvailabilityIn, user: User = Depends(owner_only), db: Session = Depends(get_db)):
    """Mark a dish as available or sold out."""
    dish = get_restaurant_dish(db, item_id, user)
    dish.is_available = data.is_available
    db.commit()
    db.refresh(dish)
    return dish


@router.delete("/menu/{item_id}", response_model=Message)
def delete_dish(item_id: int, user: User = Depends(owner_only), db: Session = Depends(get_db)):
    """Remove a dish from the menu without affecting past orders."""
    dish = get_restaurant_dish(db, item_id, user)
    # Old orders keep the dish name and price, so just unlink them
    db.execute(update(OrderItem).where(OrderItem.menu_item_id == dish.id).values(menu_item_id=None))
    db.delete(dish)
    db.commit()
    return Message(message="Dish deleted")


# ---------- Orders ----------
@router.get("/orders", response_model=Page[OrderOut])
def restaurant_orders(
    status: str | None = Query(None),
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=50),
    user: User = Depends(owner_only),
    db: Session = Depends(get_db),
):
    """List orders placed at the owner's restaurant, newest first, with optional filters."""
    restaurant = get_owner_restaurant(db, user)
    query = order_query().where(Order.restaurant_id == restaurant.id)
    return orders_page(db, apply_order_filters(query, status, date_from, date_to), page, size)


@router.patch("/orders/{order_id}/status", response_model=OrderOut)
def update_order_status(order_id: int, data: StatusUpdate, user: User = Depends(owner_only), db: Session = Depends(get_db)):
    """Move an order through the kitchen steps (accept, preparing, ready)."""
    order = get_restaurant_order(db, order_id, user)
    new_status = data.status.upper()
    # These need extra data (a partner or a refund), so they have their own endpoints
    if new_status in (OrderStatus.ASSIGNED, OrderStatus.REFUNDED):
        raise HTTPException(status_code=400, detail="Use the assign or return endpoints for this change")
    check_transition(Role.OWNER, order.status, new_status)
    set_status(order, new_status)
    db.commit()
    return order_to_out(load_order(db, order.id))


@router.get("/delivery-partners", response_model=list[DeliveryPartnerOut])
def delivery_partners(user: User = Depends(owner_only), db: Session = Depends(get_db)):
    """List all delivery partners, least busy first, so the owner can pick one."""
    # LEFT JOIN so partners with no active orders still show up with 0
    active_count = func.count(Order.id)
    rows = db.execute(
        select(User, active_count)
        .outerjoin(Order, (Order.delivery_partner_id == User.id) & Order.status.in_(ON_DELIVERY_STATUSES))
        .where(User.role == Role.DELIVERY)
        .group_by(User.id)
        .order_by(active_count, User.name)
    ).all()
    partners = []
    for partner, active_orders in rows:
        partners.append(DeliveryPartnerOut(id=partner.id, name=partner.name, phone=partner.phone,
                                           active_orders=active_orders))
    return partners


@router.post("/orders/{order_id}/assign", response_model=OrderOut)
def assign_partner(order_id: int, data: AssignIn, user: User = Depends(owner_only), db: Session = Depends(get_db)):
    """Assign a delivery partner to a READY order, moving it to ASSIGNED."""
    order = get_restaurant_order(db, order_id, user)
    if order.status != OrderStatus.READY:
        raise HTTPException(status_code=400, detail="You can assign a delivery partner only when the order is READY")
    partner = db.get(User, data.delivery_partner_id)
    if partner is None or partner.role != Role.DELIVERY:
        raise HTTPException(status_code=400, detail="That user is not a delivery partner")

    check_transition(Role.OWNER, order.status, OrderStatus.ASSIGNED)
    order.delivery_partner_id = partner.id
    set_status(order, OrderStatus.ASSIGNED)
    db.commit()
    return order_to_out(load_order(db, order.id))


# ---------- Returns and refunds ----------
@router.get("/returns", response_model=Page[OrderOut])
def return_requests(
    return_status: str = Query(ReturnStatus.REQUESTED, pattern="^(requested|approved|rejected|all)$"),
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=50),
    user: User = Depends(owner_only),
    db: Session = Depends(get_db),
):
    """List return requests for the owner's restaurant, filtered by return status."""
    restaurant = get_owner_restaurant(db, user)
    query = order_query().where(Order.restaurant_id == restaurant.id)
    # "all" means every order that ever had a return request
    if return_status == "all":
        query = query.where(Order.return_status != ReturnStatus.NONE)
    else:
        query = query.where(Order.return_status == return_status)
    return orders_page(db, query.order_by(Order.return_requested_at.desc()), page, size)


@router.post("/orders/{order_id}/return-decision", response_model=OrderOut)
def decide_return(order_id: int, data: ReturnDecisionIn, user: User = Depends(owner_only), db: Session = Depends(get_db)):
    """Approve or reject a pending return. Approving refunds the order and marks it REFUNDED."""
    order = get_restaurant_order(db, order_id, user)
    if order.return_status != ReturnStatus.REQUESTED:
        raise HTTPException(status_code=400, detail="There is no pending return request for this order")

    # A blank note is stored as NULL
    order.return_note = strip_or_none(data.note)
    if data.approve:
        check_transition(Role.OWNER, order.status, OrderStatus.REFUNDED)
        order.return_status = ReturnStatus.APPROVED
        set_status(order, OrderStatus.REFUNDED)
        record_refund(db, order, f"Return approved: {order.return_reason}")
    else:  # rejected returns leave the order DELIVERED and paid
        order.return_status = ReturnStatus.REJECTED
    db.commit()
    return order_to_out(load_order(db, order.id))


# ---------- Stats ----------
@router.get("/stats", response_model=StatsOut)
def stats(user: User = Depends(owner_only), db: Session = Depends(get_db)):
    """Dashboard numbers for the owner's restaurant: orders, revenue, refunds, ratings, top dishes."""
    restaurant = get_owner_restaurant(db, user)
    restaurant_id = restaurant.id

    # {status: count} in one GROUP BY; several totals below are derived from it
    status_rows = db.execute(
        select(Order.status, func.count(Order.id))
        .where(Order.restaurant_id == restaurant_id)
        .group_by(Order.status)
    ).all()
    status_counts = dict(status_rows)

    # Statuses with no orders are missing from status_counts, so they count as 0
    active_orders = 0
    for active_status in ACTIVE_STATUSES:
        active_orders += status_counts.get(active_status, 0)

    # "Today" is measured in UTC, matching how times are stored
    start_of_day = utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    orders_today = db.scalar(
        select(func.count(Order.id)).where(Order.restaurant_id == restaurant_id, Order.created_at >= start_of_day)
    )
    # Only DELIVERED orders count as revenue; coalesce turns "no rows" into 0
    revenue = db.scalar(
        select(func.coalesce(func.sum(Order.total_amount), 0))
        .where(Order.restaurant_id == restaurant_id, Order.status == OrderStatus.DELIVERED)
    )
    # Sum refunds from the payment ledger, which covers both cancellations and returns
    refunded = db.scalar(
        select(func.coalesce(func.sum(PaymentLedger.amount), 0))
        .join(Order, Order.id == PaymentLedger.order_id)
        .where(Order.restaurant_id == restaurant_id, PaymentLedger.entry_type == "refund")
    )
    avg_rating, review_count = db.execute(
        select(func.avg(Review.rating), func.count(Review.id)).where(Review.restaurant_id == restaurant_id)
    ).one()
    # avg() is NULL when there are no reviews yet
    if avg_rating is not None:
        avg_rating = round(avg_rating, 1)
    pending_returns = db.scalar(
        select(func.count(Order.id))
        .where(Order.restaurant_id == restaurant_id, Order.return_status == ReturnStatus.REQUESTED)
    )

    # A plain SQL query: top 5 dishes by quantity, ignoring cancelled orders
    top_rows = db.execute(
        text(
            """
            SELECT oi.name, SUM(oi.quantity) AS qty
            FROM order_items oi
            JOIN orders o ON o.id = oi.order_id
            WHERE o.restaurant_id = :restaurant_id AND o.status != 'CANCELLED'
            GROUP BY oi.name
            ORDER BY qty DESC
            LIMIT 5
            """
        ),
        {"restaurant_id": restaurant_id},
    ).all()
    top_items = [TopItem(name=dish_name, quantity=quantity) for dish_name, quantity in top_rows]

    return StatsOut(
        total_orders=sum(status_counts.values()),
        orders_today=orders_today,
        active_orders=active_orders,
        delivered_orders=status_counts.get(OrderStatus.DELIVERED, 0),
        cancelled_orders=status_counts.get(OrderStatus.CANCELLED, 0),
        revenue=round(revenue, 2),
        refunded_amount=round(refunded, 2),
        avg_rating=avg_rating,
        review_count=review_count,
        pending_returns=pending_returns,
        status_counts=status_counts,
        top_items=top_items,
    )


# ---------- Reminders ----------
@router.get("/reminders", response_model=Page[ReminderOut])
def reminders(
    background_tasks: BackgroundTasks,
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=50),
    user: User = Depends(owner_only),
    db: Session = Depends(get_db),
):
    """Reminders for orders that are still stuck. The periodic job creates them; we also
    queue one extra check after this response so the list stays fresh."""
    background_tasks.add_task(create_reminders)
    restaurant = get_owner_restaurant(db, user)
    # Only show reminders whose order is still in the status it was flagged for
    query = (
        select(ReminderLog)
        .join(Order, Order.id == ReminderLog.order_id)
        .where(ReminderLog.restaurant_id == restaurant.id, ReminderLog.order_status == Order.status)
        .order_by(ReminderLog.created_at.desc())
    )
    rows, total, pages = paginate(db, query, page, size)
    items = []
    for reminder in rows:
        items.append(ReminderOut(id=reminder.id, order_id=reminder.order_id, order_status=reminder.order_status,
                                 message=reminder.message, created_at=reminder.created_at))
    return Page[ReminderOut](items=items, total=total, page=page, size=size, pages=pages)
