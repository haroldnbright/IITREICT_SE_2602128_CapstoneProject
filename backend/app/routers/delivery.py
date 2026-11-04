"""Delivery partner endpoints. Partners only ever see orders assigned to them."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Order, OrderStatus, Role, User
from ..order_rules import check_transition
from ..schemas import OrderOut, Page, StatusUpdate
from ..security import require_role
from ..services import load_order, order_query, order_to_out, orders_page, set_status

router = APIRouter(prefix="/delivery", tags=["Delivery partner"])

delivery_only = require_role(Role.DELIVERY)

# Status groups used by the "active" and "history" scopes
ACTIVE = [OrderStatus.ASSIGNED, OrderStatus.OUT_FOR_DELIVERY]
DONE = [OrderStatus.DELIVERED, OrderStatus.REFUNDED]


@router.get("/orders", response_model=Page[OrderOut])
def my_deliveries(
    scope: str = Query("active", pattern="^(active|history|all)$"),
    status: str | None = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=50),
    user: User = Depends(delivery_only),
    db: Session = Depends(get_db),
):
    """List orders assigned to the current partner, filtered by scope or exact status."""
    query = order_query().where(Order.delivery_partner_id == user.id)
    # An explicit status filter takes priority over the scope
    if status:
        query = query.where(Order.status == status.upper())
    elif scope == "active":
        query = query.where(Order.status.in_(ACTIVE))
    elif scope == "history":
        query = query.where(Order.status.in_(DONE))
    return orders_page(db, query.order_by(Order.status_updated_at.desc()), page, size)


@router.patch("/orders/{order_id}/status", response_model=OrderOut)
def update_delivery_status(order_id: int, data: StatusUpdate, user: User = Depends(delivery_only), db: Session = Depends(get_db)):
    """Move one of the partner's orders to OUT_FOR_DELIVERY or DELIVERED."""
    order = load_order(db, order_id)
    # 404 rather than 403 so partners can't tell other orders exist
    if order.delivery_partner_id != user.id:
        raise HTTPException(status_code=404, detail="Order not found")
    new_status = data.status.upper()
    check_transition(Role.DELIVERY, order.status, new_status)
    set_status(order, new_status)
    db.commit()
    return order_to_out(load_order(db, order.id))  # reload so relations reflect the change
