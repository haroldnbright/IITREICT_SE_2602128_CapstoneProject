"""Order lifecycle rules. The backend uses these to reject invalid status changes.

PLACED -> ACCEPTED -> PREPARING -> READY -> ASSIGNED -> OUT_FOR_DELIVERY -> DELIVERED
PLACED -> CANCELLED (customer)
DELIVERED -> REFUNDED (owner approves a return)
"""
from fastapi import HTTPException

from .models import OrderStatus, Role

# Which status changes each role may make, as {role: {from_status: [allowed to_status]}}
ALLOWED_TRANSITIONS = {
    Role.CUSTOMER: {
        OrderStatus.PLACED: [OrderStatus.CANCELLED],
    },
    Role.OWNER: {
        OrderStatus.PLACED: [OrderStatus.ACCEPTED],
        OrderStatus.ACCEPTED: [OrderStatus.PREPARING],
        OrderStatus.PREPARING: [OrderStatus.READY],
        OrderStatus.READY: [OrderStatus.ASSIGNED],        # done through the assign endpoint
        OrderStatus.DELIVERED: [OrderStatus.REFUNDED],    # done through the return decision endpoint
    },
    Role.DELIVERY: {
        OrderStatus.ASSIGNED: [OrderStatus.OUT_FOR_DELIVERY],
        OrderStatus.OUT_FOR_DELIVERY: [OrderStatus.DELIVERED],
    },
}


def check_transition(role: str, current: str, new: str) -> None:
    """Raise HTTP 400 if this role can't move an order from `current` to `new`."""
    # A role or status missing from the table means no moves are allowed
    moves_for_role = ALLOWED_TRANSITIONS.get(role, {})
    allowed = moves_for_role.get(current, [])
    if new not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Can't change order from {current} to {new}",
        )
