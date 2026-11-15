# Corporate Event Management API

Backend REST API for Acme Corp's internal event management system, built with **FastAPI**, **PostgreSQL**, **SQLAlchemy 2.0 async**, and **JWT authentication**.

## Project Structure

```
app/
├── __init__.py      # Package marker
├── db.py            # Async engine, session factory, Base
├── models.py        # SQLAlchemy ORM models (User, Event, Registration)
├── schemas.py       # Pydantic request/response schemas
├── services.py      # Business logic and all database operations
└── main.py          # FastAPI app, routes, JWT dependency
tests/
├── conftest.py      # Fixtures: in-memory SQLite engine, HTTPX client, auth helper
├── test_auth.py     # Auth endpoint tests
├── test_events.py   # Event CRUD + pagination + filtering tests
└── test_registrations.py  # Registration + business-rule tests
requirements.txt
.env.example
```

## Prerequisites

- Python 3.11+
- PostgreSQL 14+ running locally (or update `DATABASE_URL` in `.env`)

## Installation

```bash
# Clone and enter the directory
git clone <your-repo-url>
cd corporate-event-management-api

# Create a virtual environment
python -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Configuration

Copy `.env.example` to `.env` and set your values:

```bash
cp .env.example .env
```

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://postgres:postgres@localhost:5432/event_db` | Async PostgreSQL connection string |
| `SECRET_KEY` | `change-me-in-production-...` | JWT signing secret — **always change in production** |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | Token lifetime in minutes |

Create the database before running:

```sql
CREATE DATABASE event_db;
```

Tables are created automatically on first startup.

## Running the API

```bash
uvicorn app.main:app --reload
```

API available at `http://127.0.0.1:8000`  
Swagger UI at `http://127.0.0.1:8000/docs`  
ReDoc at `http://127.0.0.1:8000/redoc`

## API Overview

### Auth (public)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/register` | Create a new user account |
| POST | `/auth/login` | Obtain a JWT bearer token |

### Events
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/events` | ✅ | Create event |
| GET | `/events` | ❌ | List events (pagination + filter) |
| GET | `/events/{id}` | ❌ | Get a single event |
| PUT | `/events/{id}` | ✅ | Update event fields |
| DELETE | `/events/{id}` | ✅ | Delete event |

### Registrations
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/events/{id}/registrations` | ✅ | Register for an event |
| GET | `/events/{id}/registrations` | ❌ | List registrations |
| DELETE | `/registrations/{id}` | ✅ | Cancel a registration |

**Pagination**: `GET /events?skip=0&limit=10`  
**Filtering**: `GET /events?title=Python&date=2026-12-01`

### Business Rules
- Duplicate registration → `409 Conflict`
- Event at capacity → `409 Conflict`
- Non-existent event/user → `404 Not Found`
- Missing or invalid token → `401 Unauthorized`

## Running Tests

Tests use an in-memory SQLite database — no PostgreSQL needed.

```bash
pytest -v
```

To see coverage:

```bash
pytest --cov=app --cov-report=term-missing
```

## AI Usage

This project was built with **Antigravity (Claude Sonnet 4.6 Thinking)** as a development assistant.

**Tool used**: Antigravity AI (Gemini-based agentic IDE)  
**Model**: Claude Sonnet 4.6 (Thinking)  
**Prompts used**:
1. "Build the backend API for Corporate Event Management using FastAPI and PostgreSQL following the coder-skill standards."
2. "Add full JWT auth with register/login endpoints, protecting CUD operations."
3. "Add async SQLAlchemy 2.0 with asyncpg driver."
4. "Write comprehensive pytest tests covering all endpoints and business rules using in-memory SQLite."

**All code has been reviewed and understood line by line.** The AI generated the initial structure; architecture decisions, business rule implementation, and test coverage design were verified and understood before submission.
