"""Pydantic models: what the API accepts (requests) and returns (responses)."""
from datetime import datetime
from typing import Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, EmailStr, Field

T = TypeVar("T")  # item type of a Page


class Page(BaseModel, Generic[T]):
    """Standard shape for paginated lists."""
    items: list[T]
    total: int
    page: int
    size: int
    pages: int


class Message(BaseModel):
    """Simple response carrying a human-readable message."""
    message: str


# ---------- Auth ----------
class RegisterIn(BaseModel):
    """Sign-up form for any role."""
    name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(min_length=6, max_length=72)  # bcrypt ignores bytes past 72
    role: Literal["customer", "owner", "delivery"]
    phone: str | None = Field(default=None, max_length=20)
    address: str | None = Field(default=None, max_length=255)
    # Only used when role is "owner": creates their restaurant
    restaurant_name: str | None = Field(default=None, max_length=120)
    cuisine: str | None = Field(default=None, max_length=80)


class LoginIn(BaseModel):
    """Email and password for logging in."""
    email: EmailStr
    password: str


class UserOut(BaseModel):
    """Public view of a user (never includes the password hash)."""
    # Lets the schema be built straight from an ORM object
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    email: str
    role: str
    phone: str | None
    address: str | None


class TokenOut(BaseModel):
    """Login/register response: the JWT plus the logged-in user."""
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ---------- Restaurants and menu ----------
class RestaurantOut(BaseModel):
    """A restaurant as shown to customers, with its review summary."""
    id: int
    name: str
    description: str | None
    cuisine: str | None
    address: str | None
    is_open: bool
    avg_rating: float | None = None
    review_count: int = 0


class RestaurantUpdate(BaseModel):
    """Owner's partial update of their restaurant; only sent fields change."""
    name: str | None = Field(default=None, min_length=2, max_length=120)
    description: str | None = None
    cuisine: str | None = Field(default=None, max_length=80)
    address: str | None = Field(default=None, max_length=255)
    is_open: bool | None = None


class MenuItemIn(BaseModel):
    """New dish created by an owner."""
    name: str = Field(min_length=2, max_length=120)
    description: str | None = None
    price: float = Field(gt=0, le=100000)
    category: str | None = Field(default=None, max_length=60)
    is_veg: bool = True
    is_available: bool = True


class MenuItemUpdate(BaseModel):
    """Partial update of a dish; only sent fields change."""
    name: str | None = Field(default=None, min_length=2, max_length=120)
    description: str | None = None
    price: float | None = Field(default=None, gt=0, le=100000)
    category: str | None = Field(default=None, max_length=60)
    is_veg: bool | None = None
    is_available: bool | None = None


class AvailabilityIn(BaseModel):
    """Toggle a dish in or out of stock."""
    is_available: bool


class MenuItemOut(BaseModel):
    """A dish as returned by the API."""
    model_config = ConfigDict(from_attributes=True)
    id: int
    restaurant_id: int
    name: str
    description: str | None
    price: float
    category: str | None
    is_veg: bool
    is_available: bool


# ---------- Orders ----------
class OrderItemIn(BaseModel):
    """One dish and quantity in a new order."""
    menu_item_id: int
    quantity: int = Field(ge=1, le=20)


class OrderCreate(BaseModel):
    """Customer's new order. Prices are looked up on the server, not sent by the client."""
    restaurant_id: int
    items: list[OrderItemIn] = Field(min_length=1)
    delivery_address: str = Field(min_length=5, max_length=255)


class OrderItemOut(BaseModel):
    """One line of an order, with the name and price captured at order time."""
    model_config = ConfigDict(from_attributes=True)
    id: int
    menu_item_id: int | None
    name: str
    price: float
    quantity: int


class ReviewOut(BaseModel):
    """A review as returned by the API."""
    model_config = ConfigDict(from_attributes=True)
    id: int
    order_id: int
    rating: int
    comment: str | None
    created_at: datetime
    customer_name: str | None = None


class PaymentOut(BaseModel):
    """One payment ledger entry (payment or refund)."""
    model_config = ConfigDict(from_attributes=True)
    id: int
    entry_type: str
    amount: float
    status: str
    reference: str
    note: str | None
    created_at: datetime


class OrderOut(BaseModel):
    """Full order details, flattened with restaurant, customer and partner names."""
    id: int
    status: str
    total_amount: float
    delivery_address: str
    payment_status: str
    return_status: str
    return_reason: str | None
    return_note: str | None
    created_at: datetime
    status_updated_at: datetime
    restaurant_id: int
    restaurant_name: str
    customer_name: str
    customer_phone: str | None
    delivery_partner_id: int | None
    delivery_partner_name: str | None
    items: list[OrderItemOut]
    review: ReviewOut | None
    payments: list[PaymentOut]


class StatusUpdate(BaseModel):
    """Requested new order status; checked against order_rules."""
    status: str


class AssignIn(BaseModel):
    """Delivery partner an owner assigns to a ready order."""
    delivery_partner_id: int


class ReviewIn(BaseModel):
    """Customer's rating and optional comment for a delivered order."""
    rating: int = Field(ge=1, le=5)
    comment: str | None = Field(default=None, max_length=1000)


class ReturnIn(BaseModel):
    """Customer's reason for requesting a return."""
    reason: str = Field(min_length=5, max_length=1000)


class ReturnDecisionIn(BaseModel):
    """Owner's approve/reject decision on a return, with an optional note."""
    approve: bool
    note: str | None = Field(default=None, max_length=1000)


# ---------- Owner extras ----------
class DeliveryPartnerOut(BaseModel):
    """Delivery partner an owner can pick, with how busy they are."""
    id: int
    name: str
    phone: str | None
    active_orders: int


class ReminderOut(BaseModel):
    """A stuck-order reminder shown to the owner."""
    id: int
    order_id: int
    order_status: str
    message: str
    created_at: datetime


class TopItem(BaseModel):
    """A best-selling dish and how many were sold."""
    name: str
    quantity: int


class StatsOut(BaseModel):
    """Dashboard numbers for an owner's restaurant."""
    total_orders: int
    orders_today: int
    active_orders: int
    delivered_orders: int
    cancelled_orders: int
    revenue: float
    refunded_amount: float
    avg_rating: float | None
    review_count: int
    pending_returns: int
    status_counts: dict[str, int]
    top_items: list[TopItem]


# ---------- AI ----------
class AIQuestionIn(BaseModel):
    """A question about the user's own order history."""
    question: str = Field(min_length=3, max_length=500)


class AIAnswerOut(BaseModel):
    """The AI's answer and how many orders were given to it as context."""
    answer: str
    orders_used: int
