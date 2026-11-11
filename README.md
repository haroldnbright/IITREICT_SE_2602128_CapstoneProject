# CampusBite

CampusBite is a full-stack restaurant ordering and delivery app built for campus food. Customers browse restaurants, order with a dummy payment, track orders, leave reviews, request refunds and ask an AI questions about their order history. Restaurant owners manage menus, orders, riders and refunds. Delivery partners handle the orders assigned to them.

**Submitted by:** Harold N Bright (IITREICT_SE_2602128)

## Technologies

| Layer | Stack |
|---|---|
| Frontend | React 19, React Router 7, Vite 7, JavaScript (ES6+), HTML, CSS, Fetch API |
| Backend | Python 3.14, FastAPI, Pydantic, SQLAlchemy 2 ORM, JWT (PyJWT), bcrypt |
| Database | SQLite (relational SQL, managed through SQLAlchemy) |
| AI | OpenAI API (Chat Completions) |
| DevOps | Docker, Docker Compose, Git and GitHub |

All Python and npm package versions are pinned exactly (`requirements.txt`, `package-lock.json`).

## Features

**Customer:** register and log in, browse and search restaurants, filter dishes by name, price and veg, sort the menu, cart with quantity changes (saved in localStorage), checkout with a dummy payment, order history with status and date filters and pagination, live order tracker, cancel while PLACED, rate delivered orders, request a refund with a reason, payment and refund history, AI order insights.

**Restaurant owner:** dashboard with stats (orders today, active, delivered, revenue, refunds, rating, orders by status, best sellers), reminders for orders stuck in PLACED or ACCEPTED, menu management (add, edit, delete, mark available or sold out), open or close the restaurant, order list with status and date filters, accept and move orders through preparation, assign delivery partners, approve or reject refund requests.

**Delivery partner:** current deliveries and delivery history tabs, status filter, customer name, phone and address, mark out for delivery, mark delivered.

**Security:** passwords hashed with bcrypt, JWT stored in localStorage and sent as a Bearer token, role checks on every protected endpoint, data scoped to the logged-in user (other users' orders return 404), prices always taken from the database, never from the browser.

**Backend extras:** request logging middleware (method, path, status, response time, request ID), a background job that creates reminder records, a pytest test suite.

## Project structure

```
campusbite/
├── docker-compose.yml
├── backend/
│   ├── Dockerfile
│   ├── .env.example
│   ├── requirements.txt          runtime packages
│   ├── requirements-dev.txt      plus pytest
│   ├── main.py                   app setup, middleware, startup
│   ├── app/
│   │   ├── config.py             settings from environment variables
│   │   ├── database.py           engine, session, get_db
│   │   ├── models.py             tables
│   │   ├── schemas.py            request and response models
│   │   ├── security.py           bcrypt, JWT, role checks
│   │   ├── order_rules.py        allowed status changes per role
│   │   ├── services.py           shared helpers (pagination, refunds)
│   │   ├── reminders.py          background reminder job
│   │   ├── seed.py               demo data
│   │   └── routers/              auth, restaurants, orders, owner, delivery, ai
│   └── tests/test_api.py
└── frontend/
    ├── .env.example
    ├── package.json
    └── src/
        ├── api/client.js         fetch wrapper with token
        ├── context/              AuthContext, CartContext
        ├── components/           Navbar, ProtectedRoute, OrderTicket, filters, etc.
        ├── pages/                customer, owner, delivery pages
        └── utils/                formatting, useApi hook
```

## Prerequisites

- Python 3.14
- Node.js 24 (any version from 22.12 works)
- Docker Desktop (for the Docker route)
- An OpenAI API key (only needed for AI insights)

## Environment variables

Copy `backend/.env.example` to `backend/.env` and fill it in. `.env` is in `.gitignore` and is never committed.

| Variable | Purpose | Example |
|---|---|---|
| `DATABASE_URL` | SQLAlchemy database URL | `sqlite:///./campusbite.db` |
| `JWT_SECRET_KEY` | Secret used to sign tokens | output of the command below |
| `JWT_ALGORITHM` | JWT signing algorithm | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Login lifetime | `120` |
| `OPENAI_API_KEY` | OpenAI key for AI insights | `sk-...` |
| `OPENAI_MODEL` | Model used for insights | `gpt-4o-mini` |
| `OPENAI_BASE_URL` | Empty for OpenAI, or the address of an OpenAI-compatible provider (see below) | empty |
| `AI_REQUESTS_PER_MINUTE` | AI questions allowed per user per minute | `5` |
| `AI_DAILY_LIMIT` | AI questions allowed per day across all users, `0` for no limit (resets at midnight UTC) | `100` |
| `CORS_ORIGINS` | Frontend addresses allowed to call the API | `http://localhost:5173` |
| `REMINDER_THRESHOLD_MINUTES` | Minutes before a stuck order gets a reminder | `15` |
| `REMINDER_CHECK_INTERVAL_SECONDS` | How often the reminder job runs | `60` |
| `SEED_DEMO_DATA` | Create demo data on first start | `true` |

Generate a JWT secret:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

The frontend has one variable in `frontend/.env` (copy from `frontend/.env.example`):

| Variable | Purpose | Default |
|---|---|---|
| `VITE_API_URL` | Backend address | `http://localhost:8000` |

## Quick start on Windows (PowerShell scripts)

Two scripts in the project root do everything: check tools, create `.env` files (with a generated JWT secret), create the Python venv, install packages only when they changed, start both servers in their own windows, wait until they answer, and open the browser.

One-time setup, in PowerShell from the project folder:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
Get-ChildItem -Recurse -Filter *.ps1 | Unblock-File
```

Then every time:

| Command | What it does |
|---|---|
| `.\run.ps1` | Backend in a local Python venv, plus the frontend |
| `.\run.ps1 -Docker` | Backend in Docker, plus the frontend |
| `.\run.ps1 -Reset` | Delete the database first so the demo data is recreated (works with `-Docker` too) |
| `.\run.ps1 -NoBrowser` | Don't open the browser |
| `.\stop.ps1` | Stop everything (windows, ports 8000 and 5173, Docker container). Data is kept. |

If PowerShell still says the script "is not digitally signed", use the wrappers instead. They run the same scripts with the policy bypassed for that run only, and take the same options: `.\run.cmd`, `.\run.cmd -Docker`, `.\stop.cmd`.

Add your OpenAI key to `backend\.env` (`OPENAI_API_KEY=sk-...`) after the first run, then run `.\stop.ps1` and `.\run.ps1` again.

The manual steps below do the same thing by hand.

## Run the backend with Docker Compose

From the project root:

```bash
cp backend/.env.example backend/.env      # Windows PowerShell: copy backend\.env.example backend\.env
# edit backend/.env and set JWT_SECRET_KEY and OPENAI_API_KEY
docker compose up --build
```

The API runs at http://localhost:8000 and the docs at http://localhost:8000/docs.

Docker Compose reads secrets from `backend/.env` at runtime, so they are never baked into the image. The SQLite file is stored in the named volume `campusbite-data`, so data survives restarts.

Stop it with `Ctrl+C` or `docker compose down`. To wipe the database and start fresh: `docker compose down -v`.

## Run the backend without Docker

```bash
cd backend
python -m venv venv
venv\Scripts\activate             # macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
copy .env.example .env            # macOS/Linux: cp .env.example .env
python -m uvicorn main:app --reload --reload-dir app
```

## Run the frontend

```bash
cd frontend
copy .env.example .env            # macOS/Linux: cp .env.example .env
npm ci
npm run dev
```

Open http://localhost:5173. `npm ci` installs the exact versions from `package-lock.json`.

## Database setup

No manual setup is needed. On startup the backend:

1. Creates all tables from the SQLAlchemy models (`Base.metadata.create_all`).
2. Adds demo data if the `users` table is empty and `SEED_DEMO_DATA=true`.

To reset the database, delete `backend/campusbite.db` (local run) or run `docker compose down -v` (Docker), then start again.

To use another SQL database such as PostgreSQL, change `DATABASE_URL` and install its driver. The models don't depend on SQLite.

### Tables

| Table | What it stores | Key relationships |
|---|---|---|
| `users` | All accounts, with a `role` of customer, owner or delivery | |
| `restaurants` | Restaurant details and open/closed state | `owner_id` → users |
| `menu_items` | Dishes, price, category, veg, availability | `restaurant_id` → restaurants |
| `orders` | Status, total, address, payment status, return status | `customer_id`, `delivery_partner_id` → users, `restaurant_id` → restaurants |
| `order_items` | Dishes in an order, with the name and price copied at order time | `order_id` → orders, `menu_item_id` → menu_items |
| `reviews` | Rating and comment, unique per order | `order_id` → orders |
| `payment_ledger` | Every dummy payment and refund | `order_id` → orders |
| `ai_request_logs` | One row per AI question sent to OpenAI, used for the daily limit | `user_id` → users |
| `reminder_logs` | Reminders for stuck orders, unique per order and status | `order_id` → orders |

## Demo accounts

All demo accounts use the password `password123`.

| Role | Email |
|---|---|
| Customer | customer@campusbite.com |
| Customer | customer2@campusbite.com |
| Owner (Spice Route) | owner1@campusbite.com |
| Owner (Campus Pizza Co) | owner2@campusbite.com |
| Owner (Green Bowl) | owner3@campusbite.com |
| Delivery partner | delivery1@campusbite.com |
| Delivery partner | delivery2@campusbite.com |

## Order lifecycle

```
PLACED → ACCEPTED → PREPARING → READY → ASSIGNED → OUT_FOR_DELIVERY → DELIVERED
PLACED → CANCELLED        (customer)
DELIVERED → REFUNDED      (owner approves a return)
```

| Change | Who |
|---|---|
| PLACED → CANCELLED | Customer, only while PLACED. The dummy payment is refunded. |
| PLACED → ACCEPTED → PREPARING → READY | Restaurant owner |
| READY → ASSIGNED | Restaurant owner, by assigning a delivery partner |
| ASSIGNED → OUT_FOR_DELIVERY → DELIVERED | The assigned delivery partner only |
| DELIVERED → REFUNDED | Restaurant owner, by approving a return request |

All allowed changes are defined in `backend/app/order_rules.py`. Anything else returns HTTP 400.

## Payments and refunds

Placing an order writes a `payment` row to `payment_ledger` with a `MOCKPAY-` reference and sets the order's payment status to `mock_paid`. No real gateway is used.

A customer can request a return only on a DELIVERED order, must give a reason, and can request it only once per order. If the owner approves, the order becomes REFUNDED, the payment status becomes `refunded`, and a `refund` row is added to the ledger. If the owner rejects, the return status becomes `rejected`.

## AI order insights

`POST /ai/insights` takes a question. The backend loads the logged-in customer's last 50 orders (the customer ID comes from the JWT, never the request body), adds pre-calculated totals for this week, the last 7 days and most ordered dishes, and sends that to OpenAI. The answer is shown on the AI Insights page.

Error handling: missing key returns 503, too many questions returns 429 (5 per minute per user and 100 per day across all users by default, both configurable), an OpenAI account with no credit returns 503, OpenAI rate limits return 429, timeouts return 504, and other OpenAI errors return 502.

### Using a free model during development

The AI feature uses the official OpenAI Python SDK, which can also talk to OpenAI-compatible providers. Google Gemini has a free tier with no card required, so you can develop without OpenAI credit:

1. Create a key at https://aistudio.google.com/apikey
2. In `backend\.env` set:
   ```
   OPENAI_API_KEY=<your Gemini key>
   OPENAI_MODEL=gemini-2.5-flash
   OPENAI_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
   ```
3. Restart the backend.

Clear `OPENAI_BASE_URL` and put back an OpenAI key and model to switch back to OpenAI. The code doesn't change either way.

## Middleware and background tasks

- **Middleware** (`main.py`): logs every request's method, path, status and time in milliseconds, and adds `X-Process-Time-Ms` and `X-Request-ID` response headers.
- **Background job** (`app/reminders.py`): runs every `REMINDER_CHECK_INTERVAL_SECONDS`. It finds orders in PLACED or ACCEPTED whose status hasn't changed for more than `REMINDER_THRESHOLD_MINUTES`, and creates one reminder record per order and status. Opening the reminders endpoint also queues an extra check with FastAPI `BackgroundTasks`. Reminders show on the owner dashboard until the order moves on.

## API documentation

Interactive docs are generated by FastAPI:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

To call protected endpoints in Swagger, log in with `POST /auth/login`, copy `access_token`, click **Authorize** and paste the token.

| Method | Path | Access | Purpose |
|---|---|---|---|
| POST | `/auth/register` | Public | Create an account (owners also create their restaurant) |
| POST | `/auth/login` | Public | Log in and get a JWT |
| GET | `/auth/me` | Logged in | Current user |
| GET | `/restaurants` | Public | List restaurants (search, pagination) |
| GET | `/restaurants/{id}` | Public | Restaurant details and rating |
| GET | `/restaurants/{id}/menu` | Public | Menu with search, price range, veg and sort filters |
| GET | `/restaurants/{id}/reviews` | Public | Reviews (paginated) |
| POST | `/orders` | Customer | Place an order with dummy payment |
| GET | `/orders` | Customer | Own orders (status, date filters, pagination) |
| GET | `/orders/{id}` | Customer, owner, rider | Order details, if it belongs to you |
| POST | `/orders/{id}/cancel` | Customer | Cancel a PLACED order |
| POST | `/orders/{id}/review` | Customer | Rate a delivered order |
| POST | `/orders/{id}/return` | Customer | Request a return or refund |
| GET / PUT | `/owner/restaurant` | Owner | View or update own restaurant |
| GET / POST | `/owner/menu` | Owner | List or add dishes |
| PUT / DELETE | `/owner/menu/{id}` | Owner | Edit or delete a dish |
| PATCH | `/owner/menu/{id}/availability` | Owner | Mark available or sold out |
| GET | `/owner/orders` | Owner | Restaurant orders (status, date filters, pagination) |
| PATCH | `/owner/orders/{id}/status` | Owner | Accept, prepare, mark ready |
| GET | `/owner/delivery-partners` | Owner | Riders with active order counts |
| POST | `/owner/orders/{id}/assign` | Owner | Assign a rider to a READY order |
| GET | `/owner/returns` | Owner | Return requests (paginated) |
| POST | `/owner/orders/{id}/return-decision` | Owner | Approve or reject a return |
| GET | `/owner/stats` | Owner | Restaurant statistics |
| GET | `/owner/reminders` | Owner | Reminders for stuck orders |
| GET | `/delivery/orders` | Delivery | Assigned orders (active or history, status filter) |
| PATCH | `/delivery/orders/{id}/status` | Delivery | Out for delivery, delivered |
| POST | `/ai/insights` | Customer | Ask about own order history |

Status codes used: 200, 201, 400 (rule broken), 401 (not logged in), 403 (wrong role), 404 (not found or not yours), 409 (duplicate), 422 (validation), 429 (rate limit), 502/503/504 (AI service).

## Run the tests

```bash
cd backend
pip install -r requirements-dev.txt
pytest -q
```

The tests use a temporary database and a fake OpenAI client, so they don't need a key.

## Keeping secrets out of GitHub

`.env` files, database files, `node_modules` and build output are listed in `.gitignore`. Only the `.env.example` files, which hold variable names and no secret values, are committed. Before pushing, run `git status` and confirm no `.env` file is listed.
