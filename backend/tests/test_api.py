"""End-to-end checks of the main business rules. Run with:  pytest -q"""


def place(client, headers, restaurant_id=1, qty=2):
    menu = client.get(f"/restaurants/{restaurant_id}/menu").json()
    dish = next(d for d in menu if d["is_available"])
    r = client.post("/orders", headers=headers, json={
        "restaurant_id": restaurant_id,
        "items": [{"menu_item_id": dish["id"], "quantity": qty}],
        "delivery_address": "Room 214, Hostel B",
    })
    assert r.status_code == 201, r.text
    return r.json()


def test_register_and_login(client):
    r = client.post("/auth/register", json={"name": "New User", "email": "new@x.com",
                                            "password": "secret123", "role": "customer"})
    assert r.status_code == 201
    assert client.post("/auth/register", json={"name": "New User", "email": "new@x.com",
                                                "password": "secret123", "role": "customer"}).status_code == 409
    assert client.post("/auth/login", json={"email": "new@x.com", "password": "wrong!"}).status_code == 401
    r = client.post("/auth/register", json={"name": "Shop Owner", "email": "shop@x.com", "password": "secret123",
                                            "role": "owner", "restaurant_name": "New Shop"})
    assert r.status_code == 201


def test_browse_and_filter(client):
    data = client.get("/restaurants?size=2").json()
    assert data["total"] >= 3 and len(data["items"]) == 2 and data["pages"] >= 2
    menu = client.get("/restaurants/1/menu?search=naan").json()
    assert all("naan" in d["name"].lower() for d in menu) and menu
    cheap = client.get("/restaurants/1/menu?max_price=60").json()
    assert all(d["price"] <= 60 for d in cheap)


def test_auth_required_and_roles(client, customer, owner, delivery):
    assert client.get("/orders").status_code == 401
    assert client.get("/owner/orders", headers=customer).status_code == 403
    assert client.get("/delivery/orders", headers=owner).status_code == 403
    assert client.post("/ai/insights", headers=delivery, json={"question": "hello there"}).status_code == 403


def test_price_comes_from_server_and_payment_recorded(client, customer):
    order = place(client, customer, qty=3)
    assert order["status"] == "PLACED"
    assert order["payment_status"] == "mock_paid"
    assert order["payments"][0]["entry_type"] == "payment"
    assert order["total_amount"] == round(order["items"][0]["price"] * 3, 2)


def test_unavailable_dish_and_other_restaurant_dish_rejected(client, customer, owner):
    dish = client.get("/owner/menu", headers=owner).json()[0]
    client.patch(f"/owner/menu/{dish['id']}/availability", headers=owner, json={"is_available": False})
    r = client.post("/orders", headers=customer, json={"restaurant_id": 1, "delivery_address": "Hostel B room 1",
                                                       "items": [{"menu_item_id": dish["id"], "quantity": 1}]})
    assert r.status_code == 400
    client.patch(f"/owner/menu/{dish['id']}/availability", headers=owner, json={"is_available": True})
    other = client.get("/restaurants/2/menu").json()[0]
    r = client.post("/orders", headers=customer, json={"restaurant_id": 1, "delivery_address": "Hostel B room 1",
                                                       "items": [{"menu_item_id": other["id"], "quantity": 1}]})
    assert r.status_code == 400


def test_customers_cannot_see_each_other(client, customer, customer2):
    order = place(client, customer)
    assert client.get(f"/orders/{order['id']}", headers=customer2).status_code == 404
    assert client.post(f"/orders/{order['id']}/cancel", headers=customer2).status_code == 404


def test_cancel_only_when_placed(client, customer, owner):
    order = place(client, customer)
    r = client.post(f"/orders/{order['id']}/cancel", headers=customer)
    assert r.status_code == 200 and r.json()["status"] == "CANCELLED"
    assert r.json()["payment_status"] == "refunded"

    order = place(client, customer)
    client.patch(f"/owner/orders/{order['id']}/status", headers=owner, json={"status": "ACCEPTED"})
    assert client.post(f"/orders/{order['id']}/cancel", headers=customer).status_code == 400


def test_full_lifecycle_review_and_refund(client, customer, owner, owner2, delivery, delivery2):
    order = place(client, customer)
    oid = order["id"]

    # Skipping a step is rejected
    assert client.patch(f"/owner/orders/{oid}/status", headers=owner, json={"status": "READY"}).status_code == 400
    # Another restaurant's owner can't touch it
    assert client.patch(f"/owner/orders/{oid}/status", headers=owner2, json={"status": "ACCEPTED"}).status_code == 404

    for s in ["ACCEPTED", "PREPARING"]:
        assert client.patch(f"/owner/orders/{oid}/status", headers=owner, json={"status": s}).status_code == 200

    partners = client.get("/owner/delivery-partners", headers=owner).json()
    partner_id = next(p["id"] for p in partners if p["name"] == "Aman Yadav")
    # Can't assign before READY
    assert client.post(f"/owner/orders/{oid}/assign", headers=owner,
                       json={"delivery_partner_id": partner_id}).status_code == 400
    client.patch(f"/owner/orders/{oid}/status", headers=owner, json={"status": "READY"})
    r = client.post(f"/owner/orders/{oid}/assign", headers=owner, json={"delivery_partner_id": partner_id})
    assert r.status_code == 200 and r.json()["status"] == "ASSIGNED"

    # Only the assigned partner can update, and only in order
    assert client.patch(f"/delivery/orders/{oid}/status", headers=delivery2,
                        json={"status": "OUT_FOR_DELIVERY"}).status_code == 404
    assert client.patch(f"/delivery/orders/{oid}/status", headers=delivery,
                        json={"status": "DELIVERED"}).status_code == 400
    assert client.patch(f"/delivery/orders/{oid}/status", headers=delivery,
                        json={"status": "OUT_FOR_DELIVERY"}).status_code == 200
    assert client.get(f"/orders/{oid}", headers=delivery).status_code == 200
    r = client.patch(f"/delivery/orders/{oid}/status", headers=delivery, json={"status": "DELIVERED"})
    assert r.json()["status"] == "DELIVERED"

    # Delivered orders can't be cancelled
    assert client.post(f"/orders/{oid}/cancel", headers=customer).status_code == 400

    # One review only
    assert client.post(f"/orders/{oid}/review", headers=customer, json={"rating": 4}).status_code == 201
    assert client.post(f"/orders/{oid}/review", headers=customer, json={"rating": 5}).status_code == 409

    # Return needs a reason, and only one request is allowed
    assert client.post(f"/orders/{oid}/return", headers=customer, json={"reason": ""}).status_code == 422
    assert client.post(f"/orders/{oid}/return", headers=customer, json={"reason": "Food was cold"}).status_code == 200
    assert client.post(f"/orders/{oid}/return", headers=customer, json={"reason": "Food was cold"}).status_code == 409

    returns = client.get("/owner/returns", headers=owner).json()
    assert any(o["id"] == oid for o in returns["items"])
    r = client.post(f"/owner/orders/{oid}/return-decision", headers=owner, json={"approve": True})
    body = r.json()
    assert body["status"] == "REFUNDED" and body["payment_status"] == "refunded" and body["return_status"] == "approved"
    assert [p["entry_type"] for p in body["payments"]] == ["payment", "refund"]

    history = client.get("/delivery/orders?scope=history", headers=delivery).json()
    assert any(o["id"] == oid for o in history["items"])


def test_return_rejected(client, customer):
    # Seeded order 4 was delivered by the demo data
    orders = client.get("/orders?status=DELIVERED&size=50", headers=customer).json()["items"]
    target = next(o for o in orders if o["return_status"] == "none")
    client.post(f"/orders/{target['id']}/return", headers=customer, json={"reason": "Missing an item"})
    owner_email = {"Spice Route": "owner1", "Campus Pizza Co": "owner2", "Green Bowl": "owner3"}[target["restaurant_name"]]
    from tests.conftest import login
    h = login(client, f"{owner_email}@campusbite.com")
    r = client.post(f"/owner/orders/{target['id']}/return-decision", headers=h, json={"approve": False, "note": "No"})
    assert r.json()["return_status"] == "rejected" and r.json()["status"] == "DELIVERED"


def test_filters_pagination_stats_reminders(client, owner):
    r = client.get("/owner/orders?status=PLACED&size=1", headers=owner).json()
    assert all(o["status"] == "PLACED" for o in r["items"]) and r["size"] == 1
    r = client.get("/owner/orders?date_from=2000-01-01T00:00:00Z&date_to=2000-01-02T00:00:00Z", headers=owner).json()
    assert r["total"] == 0
    stats = client.get("/owner/stats", headers=owner).json()
    assert stats["total_orders"] > 0 and stats["top_items"]
    assert client.get("/owner/reminders", headers=owner).status_code == 200


def test_reminder_job(client, owner):
    from datetime import timedelta
    from app.database import SessionLocal
    from app.models import Order, utcnow
    from app.reminders import create_reminders

    with SessionLocal() as db:
        order = db.query(Order).filter(Order.status == "PLACED", Order.restaurant_id == 1).first()
        order.status_updated_at = utcnow() - timedelta(minutes=30)
        db.commit()
        oid = order.id
    create_reminders()
    assert create_reminders() == 0  # no duplicates
    items = client.get("/owner/reminders", headers=owner).json()["items"]
    assert any(r["order_id"] == oid for r in items)


def test_ai_without_key(client, customer):
    r = client.post("/ai/insights", headers=customer, json={"question": "Summarize my last five orders"})
    assert r.status_code == 503


def test_ai_uses_only_own_orders(client, customer, monkeypatch):
    """Fake the OpenAI client and check what we send it."""
    from types import SimpleNamespace
    from app.config import settings
    import app.routers.ai as ai_module

    sent = {}

    class FakeCompletions:
        def create(self, **kwargs):
            sent["prompt"] = kwargs["messages"][1]["content"]
            msg = SimpleNamespace(content="You spent Rs 500 this week.")
            return SimpleNamespace(choices=[SimpleNamespace(message=msg)])

    class FakeClient:
        def __init__(self, **kwargs):
            self.chat = SimpleNamespace(completions=FakeCompletions())

    monkeypatch.setattr(settings, "OPENAI_API_KEY", "sk-test")
    monkeypatch.setattr(ai_module.openai, "OpenAI", FakeClient)
    r = client.post("/ai/insights", headers=customer, json={"question": "How much did I spend this week?"})
    assert r.status_code == 200 and r.json()["answer"].startswith("You spent")
    assert "Kabir" not in sent["prompt"] and "Order #7 " not in sent["prompt"]  # order 7 belongs to customer2
    assert "Spent in the last 7 days" in sent["prompt"]

    # Rate limit kicks in after AI_REQUESTS_PER_MINUTE requests
    codes = [client.post("/ai/insights", headers=customer, json={"question": "Summarize my orders"}).status_code
             for _ in range(settings.AI_REQUESTS_PER_MINUTE)]
    assert 429 in codes


def test_ai_no_credit_vs_busy(client, customer2, monkeypatch):
    """OpenAI returns 429 for both 'no credit' and 'too many requests'; we tell them apart."""
    import httpx
    import openai
    from types import SimpleNamespace
    from app.config import settings
    import app.routers.ai as ai_module

    def fake_client(code):
        class FakeCompletions:
            def create(self, **kwargs):
                request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
                response = httpx.Response(429, request=request)
                raise openai.RateLimitError("limit", response=response, body={"code": code, "message": "x"})

        class FakeClient:
            def __init__(self, **kwargs):
                self.chat = SimpleNamespace(completions=FakeCompletions())

        return FakeClient

    monkeypatch.setattr(settings, "OPENAI_API_KEY", "sk-test")
    monkeypatch.setattr(ai_module.openai, "OpenAI", fake_client("insufficient_quota"))
    r = client.post("/ai/insights", headers=customer2, json={"question": "Summarize my orders"})
    assert r.status_code == 503 and "no API credit" in r.json()["detail"]

    monkeypatch.setattr(ai_module.openai, "OpenAI", fake_client("rate_limit_exceeded"))
    r = client.post("/ai/insights", headers=customer2, json={"question": "Summarize my orders"})
    assert r.status_code == 429



def test_ai_daily_limit(client, monkeypatch):
    """Once the day's total is used up, every customer gets 429 before OpenAI is called."""
    from sqlalchemy import func, select
    from app.config import settings
    from app.database import SessionLocal
    from app.models import AIRequestLog
    from tests.conftest import login

    headers = login(client, "new@x.com", "secret123")  # fresh user, so the per-minute limit isn't hit
    place(client, headers)  # the AI is only called for customers who have orders

    with SessionLocal() as db:
        used_today = db.scalar(select(func.count(AIRequestLog.id)))
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "sk-test")
    monkeypatch.setattr(settings, "AI_DAILY_LIMIT", used_today)  # already at the limit

    r = client.post("/ai/insights", headers=headers, json={"question": "Summarize my orders"})
    assert r.status_code == 429 and "daily limit" in r.json()["detail"]


def test_ai_base_url_passed_to_sdk(client, monkeypatch):
    """OPENAI_BASE_URL is handed to the SDK; empty means OpenAI's default address."""
    from types import SimpleNamespace
    from app.config import settings
    import app.routers.ai as ai_module
    from tests.conftest import login

    seen = []

    class FakeClient:
        def __init__(self, **kwargs):
            seen.append(kwargs.get("base_url"))
            msg = SimpleNamespace(content="ok")
            completions = SimpleNamespace(create=lambda **kw: SimpleNamespace(choices=[SimpleNamespace(message=msg)]))
            self.chat = SimpleNamespace(completions=completions)

    headers = login(client, "delivery2@campusbite.com")  # wrong role is rejected before any of this
    assert client.post("/ai/insights", headers=headers, json={"question": "hello there"}).status_code == 403

    from app.database import SessionLocal
    from app.models import AIRequestLog
    with SessionLocal() as db:  # clear today's count so the daily limit doesn't interfere
        db.query(AIRequestLog).delete()
        db.commit()

    headers = login(client, "customer2@campusbite.com")
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(ai_module.openai, "OpenAI", FakeClient)
    gemini = "https://generativelanguage.googleapis.com/v1beta/openai/"
    for base_url in ("", gemini):
        monkeypatch.setattr(settings, "OPENAI_BASE_URL", base_url)
        r = client.post("/ai/insights", headers=headers, json={"question": "Summarize my orders"})
        assert r.status_code == 200, r.text
    assert seen == [None, gemini]
