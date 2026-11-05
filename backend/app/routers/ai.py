"""AI order insights. The customer's own orders are loaded from the database and sent
to OpenAI as context. The customer id always comes from the JWT, never from the request
body, so nobody can ask about someone else's orders."""
import logging
import time
from collections import Counter, defaultdict, deque
from datetime import timedelta

import openai
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..models import AIRequestLog, Order, OrderStatus, Role, User, utcnow
from ..schemas import AIAnswerOut, AIQuestionIn
from ..security import require_role
from ..services import order_query

router = APIRouter(prefix="/ai", tags=["AI insights"])
log = logging.getLogger("campusbite.ai")

# Caps the prompt size (and cost) for customers with long order histories
MAX_ORDERS_IN_CONTEXT = 50
# How many of the customer's favourite dishes to list in the context
TOP_DISHES_IN_CONTEXT = 5

# Length of the sliding window used by the per-user rate limit
RATE_LIMIT_WINDOW_SECONDS = 60

# Settings for each call to the AI model
AI_TIMEOUT_SECONDS = 30
AI_MAX_RETRIES = 2
AI_TEMPERATURE = 0.2  # low temperature keeps answers factual and consistent
AI_MAX_ANSWER_TOKENS = 500

# Simple in-memory rate limit: user id -> times of their recent requests.
# Per process and lost on restart; the daily limit below is the persistent cap
_recent_requests: dict[int, deque] = defaultdict(deque)


def check_rate_limit(user_id: int) -> None:
    """Allow at most AI_REQUESTS_PER_MINUTE questions per user in a sliding 60-second window. Raises 429."""
    # monotonic() is unaffected by system clock changes
    now = time.monotonic()
    window = _recent_requests[user_id]
    # Drop timestamps older than the window so only recent requests are counted
    while window and now - window[0] > RATE_LIMIT_WINDOW_SECONDS:
        window.popleft()
    if len(window) >= settings.AI_REQUESTS_PER_MINUTE:
        raise HTTPException(status_code=429, detail="Too many questions. Please wait a minute and try again.")
    window.append(now)


def check_daily_limit(db: Session) -> None:
    """App-wide cap on questions per day. Counted in the database, so restarting the
    backend doesn't reset it. The day starts at midnight UTC (5:30 AM in India)."""
    if settings.AI_DAILY_LIMIT <= 0:
        return
    start_of_day = utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    used_today = db.scalar(select(func.count(AIRequestLog.id)).where(AIRequestLog.created_at >= start_of_day))
    if used_today >= settings.AI_DAILY_LIMIT:
        raise HTTPException(
            status_code=429,
            detail=f"The daily limit of {settings.AI_DAILY_LIMIT} AI questions has been reached. Please try again tomorrow.",
        )


def build_context(orders: list[Order]) -> str:
    """Turn orders into plain text the model can read, plus a few pre-calculated totals."""
    now = utcnow()
    # Monday 00:00 UTC of the current week
    start_of_week = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    seven_days_ago = now - timedelta(days=7)

    # Add up spending and dish counts in one pass over the orders
    spent_this_week = 0
    spent_last_7_days = 0
    spent_total = 0
    item_counts = Counter()
    for order in orders:
        # Cancelled and refunded orders cost the customer nothing, so leave them out of totals
        if order.status in (OrderStatus.CANCELLED, OrderStatus.REFUNDED):
            continue
        spent_total += order.total_amount
        if order.created_at >= start_of_week:
            spent_this_week += order.total_amount
        if order.created_at >= seven_days_ago:
            spent_last_7_days += order.total_amount
        for item in order.items:
            item_counts[item.name] += item.quantity

    top_dishes = []
    for dish_name, quantity in item_counts.most_common(TOP_DISHES_IN_CONTEXT):
        top_dishes.append(f"{dish_name} ({quantity})")
    if top_dishes:
        top_dishes_text = ", ".join(top_dishes)
    else:
        top_dishes_text = "none"

    lines = [
        f"Current date and time (UTC): {now:%Y-%m-%d %H:%M} ({now:%A})",
        f"Orders included: {len(orders)} (newest first)",
        f"Spent since Monday this week: Rs {spent_this_week:.2f}",
        f"Spent in the last 7 days: Rs {spent_last_7_days:.2f}",
        f"Spent in total (excluding cancelled and refunded): Rs {spent_total:.2f}",
        "Most ordered dishes: " + top_dishes_text,
        "",
        "Orders:",
    ]
    # One line per order, listing every dish in it
    for order in orders:
        item_descriptions = []
        for item in order.items:
            item_descriptions.append(f"{item.quantity} x {item.name} @ Rs {item.price:.2f}")
        items_text = ", ".join(item_descriptions)
        lines.append(
            f"- Order #{order.id} | {order.created_at:%Y-%m-%d %H:%M} UTC | {order.restaurant.name} | status {order.status} | "
            f"total Rs {order.total_amount:.2f} | payment {order.payment_status} | return {order.return_status} | items: {items_text}"
        )
    return "\n".join(lines)


# Instructions sent with every question to keep answers grounded in the order data
SYSTEM_PROMPT = (
    "You help a customer of CampusBite, a food ordering app, understand their own order history. "
    "Answer only from the order data provided. If the data doesn't contain the answer, say so plainly. "
    "Use Rs for amounts. Keep answers short and clear, and use a short list when listing orders. "
    "Orders with status DELIVERED are delivered; CANCELLED and REFUNDED orders didn't cost the customer anything. "
    "If the question is not about their orders, politely say you can only help with their CampusBite orders."
)


def ask_ai(orders: list[Order], question: str) -> str:
    """Send the order data and question to the AI model and return its raw answer text.
    OpenAI errors are turned into friendly HTTP errors."""
    # An empty OPENAI_BASE_URL means OpenAI itself (the SDK's default when given None);
    # otherwise the same SDK talks to an OpenAI-compatible provider such as Google Gemini
    if settings.OPENAI_BASE_URL:
        base_url = settings.OPENAI_BASE_URL
    else:
        base_url = None
    client = openai.OpenAI(
        api_key=settings.OPENAI_API_KEY,
        base_url=base_url,
        timeout=AI_TIMEOUT_SECONDS,
        max_retries=AI_MAX_RETRIES,
    )
    try:
        completion = client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            temperature=AI_TEMPERATURE,
            max_tokens=AI_MAX_ANSWER_TOKENS,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"My order data:\n{build_context(orders)}\n\nMy question: {question}"},
            ],
        )
    except openai.RateLimitError as exc:
        # OpenAI uses HTTP 429 for two different problems:
        # "insufficient_quota" means the account has no API credit, which waiting won't fix
        log.error("OpenAI rate limit error (code=%s): %s", exc.code, exc)
        if exc.code == "insufficient_quota":
            raise HTTPException(
                status_code=503,
                detail="The OpenAI account has no API credit. Add credit in the OpenAI billing settings.",
            )
        raise HTTPException(status_code=429, detail="The AI service is busy. Please try again in a minute.")
    except openai.AuthenticationError:
        log.error("OpenAI rejected the API key")
        raise HTTPException(status_code=503, detail="The AI service is not available right now.")
    except (openai.APITimeoutError, openai.APIConnectionError):
        raise HTTPException(status_code=504, detail="The AI service took too long to respond. Please try again.")
    except openai.APIError as exc:
        log.error("OpenAI error: %s", exc)
        raise HTTPException(status_code=502, detail="The AI service is not available right now.")

    # The model may return no content at all, so treat None as an empty answer
    content = completion.choices[0].message.content
    if content is None:
        return ""
    return content.strip()


@router.post("/insights", response_model=AIAnswerOut)
def order_insights(data: AIQuestionIn, user: User = Depends(require_role(Role.CUSTOMER)), db: Session = Depends(get_db)):
    """Answer a customer's question about their own orders using the AI model.
    Rate limited per user and per day; OpenAI errors are mapped to friendly HTTP errors."""
    if not settings.OPENAI_API_KEY:
        raise HTTPException(status_code=503, detail="AI is not set up. Add OPENAI_API_KEY to the backend .env file.")
    check_rate_limit(user.id)

    # Only this customer's orders
    orders = db.scalars(
        order_query()
        .where(Order.customer_id == user.id)
        .order_by(Order.created_at.desc())
        .limit(MAX_ORDERS_IN_CONTEXT)
    ).all()
    if not orders:
        return AIAnswerOut(answer="You haven't placed any orders yet, so there's nothing to summarize.", orders_used=0)

    # Enforce the daily cap, then record this question before calling OpenAI
    # (logged first so failed or slow calls still count toward the limit)
    check_daily_limit(db)
    db.add(AIRequestLog(user_id=user.id))
    db.commit()

    answer = ask_ai(orders, data.question)
    if not answer:
        answer = "No answer was returned. Please try again."
    return AIAnswerOut(answer=answer, orders_used=len(orders))
