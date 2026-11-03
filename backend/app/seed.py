"""Demo data so the app is usable right after the first start.
Runs only when the users table is empty. All demo accounts use the password: password123
"""
import uuid
from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .models import (
    MenuItem, Order, OrderItem, OrderStatus, PaymentLedger, PaymentStatus,
    Restaurant, Review, Role, User, utcnow,
)
from .security import hash_password

DEMO_PASSWORD = "password123"

# Each restaurant: owner (name, email), details, and menu rows of (name, description, price, category, is_veg)
RESTAURANTS = [
    {
        "owner": ("Ravi Sharma", "owner1@campusbite.com"),
        "name": "Spice Route",
        "cuisine": "North Indian",
        "description": "Curries, breads and biryani cooked fresh near the main gate.",
        "address": "Shop 4, Main Gate Market",
        "menu": [
            ("Paneer Butter Masala", "Cottage cheese in a creamy tomato gravy", 220, "Mains", True),
            ("Dal Makhani", "Black lentils slow cooked overnight", 180, "Mains", True),
            ("Chicken Biryani", "Basmati rice layered with spiced chicken", 260, "Rice", False),
            ("Veg Biryani", "Basmati rice with mixed vegetables", 200, "Rice", True),
            ("Butter Naan", "Tandoor bread with butter", 45, "Breads", True),
            ("Tandoori Roti", "Whole wheat tandoor bread", 25, "Breads", True),
            ("Gulab Jamun", "Two pieces in warm syrup", 60, "Desserts", True),
        ],
    },
    {
        "owner": ("Meera Iyer", "owner2@campusbite.com"),
        "name": "Campus Pizza Co",
        "cuisine": "Pizza and Italian",
        "description": "Thin crust pizzas and pasta, open late during exams.",
        "address": "Block C, Student Centre",
        "menu": [
            ("Margherita Pizza", "Tomato, mozzarella and basil, 10 inch", 249, "Pizza", True),
            ("Farmhouse Pizza", "Onion, capsicum, mushroom and corn", 329, "Pizza", True),
            ("Chicken Tikka Pizza", "Tikka chunks, onion and mint mayo", 379, "Pizza", False),
            ("Penne Arrabbiata", "Penne in spicy tomato sauce", 229, "Pasta", True),
            ("Garlic Bread", "Four slices with herb butter", 119, "Sides", True),
            ("Cold Coffee", "Thick, with ice cream", 99, "Drinks", True),
        ],
    },
    {
        "owner": ("Arjun Mehta", "owner3@campusbite.com"),
        "name": "Green Bowl",
        "cuisine": "Healthy and Salads",
        "description": "Salads, wraps and smoothies for days you want something light.",
        "address": "Near Sports Complex",
        "menu": [
            ("Quinoa Salad Bowl", "Quinoa, chickpeas, cucumber and lemon dressing", 199, "Bowls", True),
            ("Grilled Chicken Bowl", "Brown rice, grilled chicken and greens", 249, "Bowls", False),
            ("Falafel Wrap", "Falafel, hummus and pickled veggies", 159, "Wraps", True),
            ("Paneer Tikka Wrap", "Grilled paneer with mint chutney", 169, "Wraps", True),
            ("Banana Peanut Smoothie", "Banana, peanut butter and oats", 129, "Drinks", True),
            ("Fresh Lime Soda", "Sweet or salted", 59, "Drinks", True),
        ],
    },
]


def _user(name: str, email: str, role: str, phone: str, address: str | None = None) -> User:
    """Build a demo user with the shared demo password."""
    return User(name=name, email=email, role=role, phone=phone, address=address,
                password_hash=hash_password(DEMO_PASSWORD))


def _demo_order(db: Session, customer: User, restaurant: Restaurant, lines: list[tuple[MenuItem, int]],
                status: str, days_ago: float, partner: User | None = None, rating: int | None = None) -> None:
    """Add a backdated order with its items, mock payment, and optional refund and review."""
    created = utcnow() - timedelta(days=days_ago)
    # Never in the future, even for orders placed only minutes ago
    status_updated_at = min(created + timedelta(minutes=40), utcnow())
    if partner:
        partner_id = partner.id
    else:
        partner_id = None

    total = 0
    for dish, quantity in lines:
        total += dish.price * quantity

    order = Order(
        customer_id=customer.id, restaurant_id=restaurant.id, status=status,
        delivery_address=customer.address, created_at=created,
        status_updated_at=status_updated_at,
        delivery_partner_id=partner_id,
        total_amount=round(total, 2),
        payment_status=PaymentStatus.MOCK_PAID,
    )
    for dish, quantity in lines:
        order.items.append(OrderItem(menu_item_id=dish.id, name=dish.name, price=dish.price, quantity=quantity))
    db.add(order)
    db.flush()  # need order.id for the ledger rows below

    db.add(PaymentLedger(
        order_id=order.id,
        entry_type="payment",
        amount=order.total_amount,
        status=PaymentStatus.MOCK_PAID,
        reference=f"MOCKPAY-{uuid.uuid4().hex[:10].upper()}",
        note="Dummy payment, no money was charged",
        created_at=created,
    ))
    # Cancelled orders get refunded, same as when a real customer cancels
    if status == OrderStatus.CANCELLED:
        order.payment_status = PaymentStatus.REFUNDED
        db.add(PaymentLedger(
            order_id=order.id,
            entry_type="refund",
            amount=order.total_amount,
            status=PaymentStatus.REFUNDED,
            reference=f"MOCKREF-{uuid.uuid4().hex[:10].upper()}",
            note="Order cancelled by customer",
            created_at=created + timedelta(minutes=2),
        ))
    if rating:
        db.add(Review(order_id=order.id, customer_id=customer.id, restaurant_id=restaurant.id,
                      rating=rating, comment="Hot and on time.", created_at=created + timedelta(hours=1)))


def seed_demo_data(db: Session) -> None:
    """Fill an empty database with demo users, restaurants, menus and orders."""
    # Any existing user means the database is already in use, so leave it alone
    if db.scalar(select(func.count(User.id))) > 0:
        return

    customer = _user("Priya Verma", "customer@campusbite.com", Role.CUSTOMER, "9876500001",
                     "Room 214, Hostel B, North Campus")
    customer2 = _user("Kabir Singh", "customer2@campusbite.com", Role.CUSTOMER, "9876500002",
                      "Room 108, Hostel A, North Campus")
    partner1 = _user("Aman Yadav", "delivery1@campusbite.com", Role.DELIVERY, "9876500101")
    partner2 = _user("Sunil Kumar", "delivery2@campusbite.com", Role.DELIVERY, "9876500102")
    db.add_all([customer, customer2, partner1, partner2])

    restaurants = []
    for index, spec in enumerate(RESTAURANTS):
        owner_name, owner_email = spec["owner"]
        # Owner phone numbers end in 00, 01, 02, ...
        owner = _user(owner_name, owner_email, Role.OWNER, f"98765002{index:02d}")
        db.add(owner)
        db.flush()  # need owner.id for the restaurant
        restaurant = Restaurant(owner_id=owner.id, name=spec["name"], cuisine=spec["cuisine"],
                                description=spec["description"], address=spec["address"])
        for name, description, price, category, is_veg in spec["menu"]:
            restaurant.menu_items.append(
                MenuItem(name=name, description=description, price=price, category=category, is_veg=is_veg)
            )
        db.add(restaurant)
        restaurants.append(restaurant)
    db.flush()  # assign menu item ids so demo orders can reference them

    spice, pizza, green = restaurants
    spice_menu = spice.menu_items
    pizza_menu = pizza.menu_items
    green_menu = green.menu_items

    # A short order history for the main demo customer; each line is (dish, quantity)
    _demo_order(db, customer, spice, [(spice_menu[0], 1), (spice_menu[4], 3)],
                OrderStatus.DELIVERED, 12, partner1, rating=5)
    _demo_order(db, customer, pizza, [(pizza_menu[0], 1), (pizza_menu[4], 1)],
                OrderStatus.DELIVERED, 8, partner2, rating=4)
    _demo_order(db, customer, green, [(green_menu[0], 1), (green_menu[4], 1)],
                OrderStatus.DELIVERED, 4, partner1)
    _demo_order(db, customer, spice, [(spice_menu[3], 1), (spice_menu[4], 2), (spice_menu[6], 1)],
                OrderStatus.DELIVERED, 2, partner2)
    _demo_order(db, customer, pizza, [(pizza_menu[1], 1)], OrderStatus.CANCELLED, 1.5)
    _demo_order(db, customer, spice, [(spice_menu[1], 1), (spice_menu[4], 2)], OrderStatus.READY, 0.05)
    # One fresh order from the second customer, so the owner has something to accept
    _demo_order(db, customer2, spice, [(spice_menu[2], 2)], OrderStatus.PLACED, 0.02)

    db.commit()
