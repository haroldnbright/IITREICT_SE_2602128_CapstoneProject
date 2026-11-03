"""Background job: remind owners about orders stuck in PLACED or ACCEPTED.

start_reminder_loop() runs forever while the app is up (started in main.py).
Every REMINDER_CHECK_INTERVAL_SECONDS it calls create_reminders().
"""
import asyncio
import logging
from datetime import timedelta

from sqlalchemy import select

from .config import settings
from .database import SessionLocal
from .models import Order, OrderStatus, ReminderLog, utcnow

log = logging.getLogger("campusbite.reminders")


def create_reminders() -> int:
    """Create one reminder for each stuck order that doesn't have one yet. Returns how many were made."""
    db = SessionLocal()
    try:
        # Orders whose status hasn't changed since before this time count as stuck
        cutoff = utcnow() - timedelta(minutes=settings.REMINDER_THRESHOLD_MINUTES)
        stuck_orders = db.scalars(
            select(Order).where(
                Order.status.in_([OrderStatus.PLACED, OrderStatus.ACCEPTED]),
                Order.status_updated_at < cutoff,
            )
        ).all()

        created = 0
        for order in stuck_orders:
            # Skip orders already reminded about for this same status
            existing_reminder = db.scalars(
                select(ReminderLog).where(ReminderLog.order_id == order.id, ReminderLog.order_status == order.status)
            ).first()
            if existing_reminder:
                continue
            # Whole minutes the order has been waiting in its current status
            waiting_seconds = (utcnow() - order.status_updated_at).total_seconds()
            minutes = int(waiting_seconds // 60)
            db.add(
                ReminderLog(
                    order_id=order.id,
                    restaurant_id=order.restaurant_id,
                    order_status=order.status,
                    message=f"Order #{order.id} has been {order.status} for {minutes} minutes",
                )
            )
            created += 1
        db.commit()
        if created:
            log.info("Created %s reminder(s)", created)
        return created
    except Exception:
        db.rollback()  # e.g. two checks inserting the same reminder at once
        log.exception("Reminder check failed")
        return 0
    finally:
        db.close()


async def start_reminder_loop() -> None:
    """Check for stuck orders forever on a fixed interval. Cancelled by main.py on shutdown."""
    while True:
        # Run the database work in a thread so it doesn't block API requests
        await asyncio.to_thread(create_reminders)
        await asyncio.sleep(settings.REMINDER_CHECK_INTERVAL_SECONDS)
