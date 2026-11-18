# Assignment 03: Corporate Event Management API
## Requirements Compliance Matrix & Verification Evidence

**Project**: Corporate Event Management API (Acme Corp Internal Event System)  
**Status**: 100% Fully Compliant across all Mandatory Requirements & All 5 Bonus Criteria  

---

### 1. Project Architecture & Code Organization

| Requirement Spec (Assignment PDF Sec. 2) | Status | Code Location | Verification Evidence |
|---|:---:|---|---|
| `db.py`: Database connection & configuration | **COMPLIANT** | `app/db.py` | `create_async_engine`, `async_sessionmaker`, `get_db` async generator |
| `models.py`: SQLAlchemy database models | **COMPLIANT** | `app/models.py` | `User`, `Event`, `Registration` declarative models with relations & CASCADE |
| `schemas.py`: Pydantic schemas for validation/responses | **COMPLIANT** | `app/schemas.py` | `UserCreate`, `EventCreate`, `EventUpdate`, `RegistrationCreate`, `PaginatedEvents` |
| `services.py`: Pure business logic & DB operations | **COMPLIANT** | `app/services.py` | All queries/mutations isolated from routes; async queries & business rules |
| `main.py`: API routes & application entry point | **COMPLIANT** | `app/main.py` | FastAPI app, CORS middleware, route routers, exception mapping, JWT injection |

---

### 2. Mandatory Features — Event Management CRUD

| Endpoint / Operation | HTTP Verb | Status | Handler / Implementation | Verification Evidence |
|---|:---:|:---:|---|---|
| Create a new event | `POST /events` | **COMPLIANT** | `app/services.py:create_event` | HTTP `201 Created`, returns ID & timestamps (`test_create_event`) |
| Retrieve all events | `GET /events` | **COMPLIANT** | `app/services.py:get_events` | HTTP `200 OK`, returns paginated items + total (`test_get_events`) |
| Retrieve specific event | `GET /events/{id}` | **COMPLIANT** | `app/services.py:get_event_by_id` | HTTP `200 OK`, HTTP `404 Not Found` if missing (`test_get_event_by_id`) |
| Update an existing event | `PUT /events/{id}` | **COMPLIANT** | `app/services.py:update_event` | HTTP `200 OK`, partial updates supported (`test_update_event_partial`) |
| Delete an event | `DELETE /events/{id}` | **COMPLIANT** | `app/services.py:delete_event` | HTTP `204 No Content`, cascades child records (`test_delete_event`) |
| Event entity required fields | — | **COMPLIANT** | `app/models.py:Event` | ID, title, description, event_date, location, max_capacity |

---

### 3. Mandatory Features — Event Registration & Business Rules

| Business Rule / Endpoint | HTTP Verb | Status | Implementation Detail | Verification Evidence |
|---|:---:|:---:|---|---|
| Register for an event | `POST /events/{id}/registrations` | **COMPLIANT** | `app/services.py:create_registration` | HTTP `201 Created`, records `registered_at` (`test_register_success`) |
| View all registrations for an event | `GET /events/{id}/registrations` | **COMPLIANT** | `app/services.py:get_event_registrations` | HTTP `200 OK`, returns attendee list (`test_get_registrations`) |
| Cancel a registration | `DELETE /registrations/{id}` | **COMPLIANT** | `app/services.py:cancel_registration` | HTTP `204 No Content` (`test_cancel_registration`) |
| **Rule 1**: No duplicate registration | — | **COMPLIANT** | Checked via `select(Registration).where(...)` | HTTP `409 Conflict: User is already registered` (`test_register_duplicate_rejected`) |
| **Rule 2**: Enforce maximum capacity limit | — | **COMPLIANT** | Checked via `func.count(Registration.id) >= event.max_capacity` | HTTP `409 Conflict: Event has reached its maximum capacity` (`test_register_capacity_limit_enforced`) |
| **Rule 3**: Reject non-existent events/users | — | **COMPLIANT** | Verified prior to registration creation | HTTP `404 Not Found: Event/User not found` (`test_register_nonexistent_event`) |

---

### 4. Pydantic Validation & HTTP Status Codes

| Standard / Code | Expected Scenario | Status | Implementation |
|:---:|---|:---:|---|
| **200 OK** | Successful read or update | **COMPLIANT** | `GET /events`, `GET /events/{id}`, `PUT /events/{id}`, `POST /auth/login` |
| **201 Created** | Successful creation | **COMPLIANT** | `POST /events`, `POST /events/{id}/registrations`, `POST /auth/register` |
| **204 No Content** | Successful deletion | **COMPLIANT** | `DELETE /events/{id}`, `DELETE /registrations/{id}` |
| **401 Unauthorized** | Missing or invalid JWT bearer token | **COMPLIANT** | Enforced via `Depends(get_current_user)` on CUD endpoints |
| **404 Not Found** | Target resource does not exist | **COMPLIANT** | Event or registration not found triggers `HTTPException(status_code=404)` |
| **409 Conflict** | Duplicate registration, capacity limit exceeded, duplicate email/user | **COMPLIANT** | Handled with precise descriptive error messages |
| **422 Unprocessable** | Blank title, zero/negative capacity, invalid username chars | **COMPLIANT** | Pydantic field validators with whitespace stripping and regex |

---

### 5. Bonus Features Evaluation

| Bonus Category | Assignment Rubric Spec | Status | Implementation Detail |
|---|---|:---:|---|
| **A. Pagination** | `skip` & `limit` query parameters | **COMPLIANT** | `GET /events?skip=0&limit=10` returning `PaginatedEvents(total, skip, limit, items)` |
| **B. Search & Filtering** | Filter by `title` substring and `date` | **COMPLIANT** | `GET /events?title=Python&date=2026-12-01` using `ilike()` and `cast(event_date, Date)` |
| **C. JWT Authentication** | Auth token, protect CUD, public reads | **COMPLIANT** | Zero-dependency HS256 JWT, scrypt password hashing, Bearer auth dependency |
| **D. Async Database Ops** | SQLAlchemy 2.0 Async Engine & sessions | **COMPLIANT** | `create_async_engine`, `asyncpg`, 100% async/await across all service operations |
| **E. Unit Testing** | Comprehensive `pytest` test suite | **COMPLIANT** | 31 unit tests in `tests/` using in-memory SQLite (`aiosqlite`) + HTTPX async client |
| **Frontend (Recommended)** | Web interface demonstrating API | **COMPLIANT** | Modern single-page UI at `/` (`static/index.html`) with live auth, cards & capacity bars |

---

### 6. Git & GitHub Engineering Standards

| Rubric Criteria | Status | Evidence / Verification |
|---|:---:|---|
| Public GitHub repository created | **COMPLIANT** | `https://github.com/salmanzaman777/corporate-event-management-api` |
| `main` used as stable production branch | **COMPLIANT** | `main` is default, stable, clean production branch |
| Feature branches for individual modules | **COMPLIANT** | `feature/event-crud`, `feature/jwt-auth`, `feature/registrations`, `feature/async-db`, `feature/pagination-search`, `feature/tests`, `feature/frontend` |
| Atomic, descriptive commit history | **COMPLIANT** | Conventional commits (`feat:`, `refactor:`, `test:`, `docs:`, `merge:`) |
| All feature branches cleanly merged into `main` | **COMPLIANT** | Verified via `git log --graph --oneline --all` |

---

### 7. Submission Deliverables Checklist

| Deliverable | Location / Artifact | Status |
|---|---|:---:|
| 1. Public GitHub Repository Link | `https://github.com/salmanzaman777/corporate-event-management-api` | **READY** |
| 2. Complete Source Code | `app/`, `static/`, `tests/` | **COMPLETE** |
| 3. Dependency Manifest | `requirements.txt` | **COMPLETE** |
| 4. Technical Documentation | `README.md` (Architecture, Setup, Execution) | **COMPLETE** |
| 5. Requirements Compliance Matrix | `COMPLIANCE_MATRIX.md` | **COMPLETE** |
| 6. AI Usage Disclosure | Documented in `README.md` (Tool, Model, Prompts, Review) | **COMPLETE** |
