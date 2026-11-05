"""CampusBite API entry point. Run with:  uvicorn main:app --reload"""
import asyncio
import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import Base, SessionLocal, engine
from app.reminders import start_reminder_loop
from app.routers import ai, auth, delivery, orders, owner, restaurants
from app.seed import seed_demo_data

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("campusbite")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Run startup work before the app serves requests and clean up on shutdown."""
    # Startup: create tables, add demo data, start the reminder job
    if settings.JWT_SECRET_KEY == "change-me":
        log.warning("JWT_SECRET_KEY is not set. Set it in backend/.env before sharing this app.")
    Base.metadata.create_all(bind=engine)
    if settings.SEED_DEMO_DATA:
        with SessionLocal() as db:
            seed_demo_data(db)
    reminder_task = asyncio.create_task(start_reminder_loop())
    log.info("CampusBite API started")
    yield
    # Shutdown: stop the reminder job
    reminder_task.cancel()


app = FastAPI(
    title="CampusBite API",
    description="Restaurant ordering and delivery platform. Use /auth/login, then click Authorize and paste the token.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    # Let the browser frontend read our custom headers
    expose_headers=["X-Process-Time-Ms", "X-Request-ID"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log method, path, status and how long each request took.
    Also gives each request an id and returns timing in a response header."""
    # Reuse the caller's request id if it sent one, so logs can be traced end to end
    request_id = request.headers.get("X-Request-ID")
    if not request_id:
        # Otherwise make a short random id
        request_id = uuid.uuid4().hex[:8]
    request.state.request_id = request_id
    start = time.perf_counter()

    response = await call_next(request)

    duration_ms = (time.perf_counter() - start) * 1000
    response.headers["X-Process-Time-Ms"] = f"{duration_ms:.1f}"
    response.headers["X-Request-ID"] = request_id
    log.info("[%s] %s %s -> %s in %.1f ms", request_id, request.method, request.url.path,
             response.status_code, duration_ms)
    return response


# Register every feature router on the app
app.include_router(auth.router)
app.include_router(restaurants.router)
app.include_router(orders.router)
app.include_router(owner.router)
app.include_router(delivery.router)
app.include_router(ai.router)


@app.get("/", tags=["Health"])
def health():
    """Health check so you can confirm the API is up."""
    return {"status": "ok", "app": "CampusBite API", "docs": "/docs"}
