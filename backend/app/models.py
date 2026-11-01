"""Database tables (SQLAlchemy ORM models)."""
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def utcnow() -> datetime:
    """Current UTC time without tzinfo. All times are stored in UTC."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ---- Fixed values used across the app ----
class Role:
    """User roles, which decide what each account is allowed to do."""

    CUSTOMER = "customer"
    OWNER = "owner"
    DELIVERY = "delivery"


class OrderStatus:
    """Every status an order can be in (see order_rules.py for allowed moves)."""

    PLACED = "PLACED"
    ACCEPTED = "ACCEPTED"
    PREPARING = "PREPARING"
    READY = "READY"
    ASSIGNED = "ASSIGNED"
    OUT_FOR_DELIVERY = "OUT_FOR_DELIVERY"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"
    REFUNDED = "REFUNDED"


class PaymentStatus:
    """Payment state of an order. Payments are simulated, so there is no real gateway."""

    PENDING = "pending"
    MOCK_PAID = "mock_paid"
    REFUNDED = "refunded"


class ReturnStatus:
    """Where a customer's return request stands."""

    NONE = "none"
    REQUESTED = "requested"
    APPROVED = "approved"
    REJECTED = "rejected"


# ---- Tables ----
class User(Base):
    """An account: a customer, a restaurant owner or a delivery partner."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), index=True)
    phone: Mapped[str | None] = mapped_column(String(20))
    address: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    restaurants: Mapped[list["Restaurant"]] = relationship(back_populates="owner")
    orders: Mapped[list["Order"]] = relationship(back_populates="customer", foreign_keys="Order.customer_id")
    deliveries: Mapped[list["Order"]] = relationship(
        back_populates="delivery_partner", foreign_keys="Order.delivery_partner_id"
    )


class Restaurant(Base):
    """A restaurant listed on the platform, run by one owner."""

    __tablename__ = "restaurants"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str | None] = mapped_column(Text)
    cuisine: Mapped[str | None] = mapped_column(String(80))
    address: Mapped[str | None] = mapped_column(String(255))
    is_open: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    owner: Mapped["User"] = relationship(back_populates="restaurants")
    menu_items: Mapped[list["MenuItem"]] = relationship(back_populates="restaurant")
    orders: Mapped[list["Order"]] = relationship(back_populates="restaurant")


class MenuItem(Base):
    """A dish on a restaurant's menu."""

    __tablename__ = "menu_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    restaurant_id: Mapped[int] = mapped_column(ForeignKey("restaurants.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str | None] = mapped_column(Text)
    price: Mapped[float] = mapped_column(Float)
    category: Mapped[str | None] = mapped_column(String(60))
    is_veg: Mapped[bool] = mapped_column(Boolean, default=True)
    # Owners hide sold-out dishes with this instead of deleting them
    is_available: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    restaurant: Mapped["Restaurant"] = relationship(back_populates="menu_items")


class Order(Base):
    """A customer's order from one restaurant, tracked through delivery and any return."""

    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    restaurant_id: Mapped[int] = mapped_column(ForeignKey("restaurants.id"), index=True)
    delivery_partner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)

    status: Mapped[str] = mapped_column(String(20), default=OrderStatus.PLACED, index=True)
    total_amount: Mapped[float] = mapped_column(Float)
    delivery_address: Mapped[str] = mapped_column(String(255))
    payment_status: Mapped[str] = mapped_column(String(20), default=PaymentStatus.PENDING)

    return_status: Mapped[str] = mapped_column(String(20), default=ReturnStatus.NONE)
    return_reason: Mapped[str | None] = mapped_column(Text)
    return_note: Mapped[str | None] = mapped_column(Text)  # owner's note when deciding
    return_requested_at: Mapped[datetime | None] = mapped_column(DateTime)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    # Reset on every status change; the reminder job uses it to spot stuck orders
    status_updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    # Two foreign keys point at users, so each relationship names which one it uses
    customer: Mapped["User"] = relationship(back_populates="orders", foreign_keys=[customer_id])
    delivery_partner: Mapped["User | None"] = relationship(
        back_populates="deliveries", foreign_keys=[delivery_partner_id]
    )
    restaurant: Mapped["Restaurant"] = relationship(back_populates="orders")
    items: Mapped[list["OrderItem"]] = relationship(back_populates="order", cascade="all, delete-orphan")
    review: Mapped["Review | None"] = relationship(back_populates="order", uselist=False)
    payments: Mapped[list["PaymentLedger"]] = relationship(back_populates="order")


class OrderItem(Base):
    """One line of an order: a dish and how many were ordered."""

    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), index=True)
    # Nullable so a dish can be deleted from the menu without breaking old orders
    menu_item_id: Mapped[int | None] = mapped_column(ForeignKey("menu_items.id", ondelete="SET NULL"))
    # Name and price are copied at order time, so later menu edits don't change old orders
    name: Mapped[str] = mapped_column(String(120))
    price: Mapped[float] = mapped_column(Float)
    quantity: Mapped[int] = mapped_column(Integer)

    order: Mapped["Order"] = relationship(back_populates="items")


class Review(Base):
    """A customer's rating and comment for a delivered order."""

    __tablename__ = "reviews"
    __table_args__ = (UniqueConstraint("order_id", name="uq_review_order"),)  # one review per order

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"))
    customer_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    # Stored directly (not only via the order) so restaurant ratings are quick to average
    restaurant_id: Mapped[int] = mapped_column(ForeignKey("restaurants.id"), index=True)
    rating: Mapped[int] = mapped_column(Integer)
    comment: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    order: Mapped["Order"] = relationship(back_populates="review")
    customer: Mapped["User"] = relationship()


class PaymentLedger(Base):
    """Every money movement for an order: the dummy payment and any refund."""

    __tablename__ = "payment_ledger"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), index=True)
    entry_type: Mapped[str] = mapped_column(String(20))  # "payment" or "refund"
    amount: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(20))  # "mock_paid" or "refunded"
    reference: Mapped[str] = mapped_column(String(60))
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    order: Mapped["Order"] = relationship(back_populates="payments")


class ReminderLog(Base):
    """Created by the background job when an order sits in PLACED/ACCEPTED too long."""

    __tablename__ = "reminder_logs"
    # Only one reminder per order per status
    __table_args__ = (UniqueConstraint("order_id", "order_status", name="uq_reminder_order_status"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), index=True)
    restaurant_id: Mapped[int] = mapped_column(ForeignKey("restaurants.id"), index=True)
    order_status: Mapped[str] = mapped_column(String(20))
    message: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    order: Mapped["Order"] = relationship()


class AIRequestLog(Base):
    """One row per question sent to OpenAI. Used for the daily limit and as an audit trail."""

    __tablename__ = "ai_request_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
