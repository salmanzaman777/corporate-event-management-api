# Corporate Event Management API — Complete Project Demo Guide

A sequenced, step-by-step walkthrough covering all **C.R.U.D.** operations, business-rule enforcement, JWT authentication, and edge-case validations. Use this guide directly as your demo video script or evaluation runbook.

---

## Prerequisites & Launch

### 1. Start the Backend Server
Open your terminal in the `Solution/` directory:
```bash
python -m uvicorn app.main:app --reload
```
- **Web Application**: Open [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- **Swagger OpenAPI Docs**: Open [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc Documentation**: Open [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

---

## Sequenced Demo Walkthrough (18 Key Activity Points)

### Part 1: Authentication & Security (Auth CRUD)

#### Activity 1: Verify Unauthenticated Guard (Security / 401 Unauthorized)
- **Action**: In the web UI or Swagger, attempt to click **"+ New Event"** while logged out as `Guest`.
- **Expected Result**: System rejects the action with a toast: `"Authentication required to create events"`. In HTTP/Swagger, the server returns `401 Unauthorized` containing the RFC 6750 compliant header `WWW-Authenticate: Bearer`.

#### Activity 2: Register a New Employee Account (`POST /auth/register`)
- **Action**: Click **"Sign In"** → **"Need an account? Register"**.
- **Inputs**:
  - Username: `alice_engineer`
  - Email: `alice@acmecorp.com`
  - Password: `Password123!`
- **Expected Result**: HTTP `201 Created`. The user profile is created with hashed password (`scrypt`) and user ID assigned. Notice password digests are never returned in responses.

#### Activity 3: Test Username Validation Edge Case (Validation / 422 Unprocessable Entity)
- **Action**: Try registering a user with spaces or special characters (e.g., `user!name@`).
- **Expected Result**: HTTP `422 Unprocessable Entity` with error: `"username may only contain letters, numbers, and underscores"`.

#### Activity 4: User Authentication & Token Generation (`POST /auth/login`)
- **Action**: In the Sign In modal, enter `alice_engineer` and `Password123!` (or use the one-click **"Fill Demo User"** button for `salman_dev`).
- **Expected Result**: HTTP `200 OK`. Server issues a signed HS256 JWT bearer token. Top-right pill updates to `@alice_engineer` with an active green indicator.

---

### Part 2: Event Management (Events CRUD)

#### Activity 5: Read All Events with Pagination (`GET /events?skip=0&limit=6`)
- **Action**: Observe the event catalog grid.
- **Expected Result**: HTTP `200 OK`. The server returns a paginated payload (`total`, `skip`, `limit`, and `items`). Notice the pagination bar indicates `Page 1 of 1 (6 events)`.

#### Activity 6: Filter by Title Substring (`GET /events?title=Workshop`)
- **Action**: Type `Workshop` into the search bar.
- **Expected Result**: HTTP `200 OK`. Grid dynamically filters to only events containing "Workshop" (e.g., *Hands-On FastAPI & SQLAlchemy 2.0 Workshop*).

#### Activity 7: Filter by Category Card (Top 6 Showcase)
- **Action**: Click the **"🚀 Product Launch"** or **"🎤 Conference"** banner card.
- **Expected Result**: Search input instantly populates with the category keyword and re-queries the backend.

#### Activity 8: Filter by Exact Calendar Date (`GET /events?date=YYYY-MM-DD`)
- **Action**: Select a calendar date in the date picker input.
- **Expected Result**: HTTP `200 OK`. Only events scheduled on that specific calendar day are returned.

#### Activity 9: Create a New Corporate Event (`POST /events`)
- **Action**: Click **"+ New Event"**.
- **Inputs**:
  - Title: `⚡ Autonomous AI Agents Hackathon 2026`
  - Description: `48-hour internal hackathon building autonomous tool-calling workflows.`
  - Date & Time: Select any date next week
  - Location: `Acme Innovation Hub · Floor 4`
  - Max Capacity: `2` (set to 2 so we can easily test capacity limits in Part 3)
- **Expected Result**: HTTP `201 Created`. Event appears immediately on the catalog grid with `0 / 2 Seats (0%)`.

#### Activity 10: Test Event Validation Edge Cases (Validation / 422)
- **Action**: Try creating an event with whitespace-only title (`"   "`) or zero capacity (`0`).
- **Expected Result**: HTTP `422 Unprocessable Entity`. Pydantic validator blocks blank titles and non-positive capacity before hitting the database.

#### Activity 11: Read Specific Event Details by ID (`GET /events/{id}`)
- **Action**: In Swagger UI or browser, query `GET /events/{new_event_id}`.
- **Expected Result**: HTTP `200 OK` returning full entity details including `created_at` and `updated_at`.

#### Activity 12: Partial Update of an Event (`PUT /events/{id}`)
- **Action**: In Swagger UI, submit a PUT request to update only the location:
  ```json
  {
    "location": "Acme Sky Lounge · Executive Tower"
  }
  ```
- **Expected Result**: HTTP `200 OK`. Only the location field changes; other attributes remain untouched, and `updated_at` updates to current timestamp.

#### Activity 13: Delete an Event (`DELETE /events/{id}`)
- **Action**: Click the red **"✕"** button on a test event card and confirm.
- **Expected Result**: HTTP `204 No Content`. Event and any child registrations are cascaded and permanently deleted. Subsequent fetch returns `404 Not Found`.

---

### Part 3: Attendee Registrations & Business Rules (Registrations CRUD)

#### Activity 14: Register for an Event (`POST /events/{id}/registrations`)
- **Action**: On the `Autonomous AI Agents Hackathon` card (capacity: 2), click **"Register"**.
- **Expected Result**: HTTP `201 Created`. Toast confirms registration. Progress bar advances to `1 / 2 Seats (50%)`.

#### Activity 15: Enforce Business Rule 1 — No Duplicate Registrations (409 Conflict)
- **Action**: Immediately click **"Register"** again on the same event card.
- **Expected Result**: HTTP `409 Conflict`. Server returns message: `"User is already registered for event"`. Duplicate entry is rejected.

#### Activity 16: Enforce Business Rule 2 — Maximum Capacity Ceiling (409 Conflict)
- **Action**:
  1. Sign in as another user (or submit registration for user ID 2 via Swagger).
  2. The event now reaches `2 / 2 Seats (100%)`, turning the capacity bar red.
  3. Attempt to register a 3rd user for this event.
- **Expected Result**: HTTP `409 Conflict`. Server returns message: `"Event has reached its maximum capacity of 2"`. Overbooking is strictly prevented.

#### Activity 17: Inspect Event Attendees List (`GET /events/{id}/registrations`)
- **Action**: Click **"Attendees"** on the event card.
- **Expected Result**: HTTP `200 OK`. A modal opens showing all registered attendee IDs and registration timestamps.

#### Activity 18: Cancel / Delete a Registration (`DELETE /registrations/{id}`)
- **Action**: Inside the Attendees modal, click **"Cancel"** next to an attendee.
- **Expected Result**: HTTP `204 No Content`. Registration record is deleted, attendee is removed from the modal, and the card capacity drops back to `1 / 2 Seats (50%)`, opening a seat for others.

---

## Part 4: Automated Verification (pytest)

Run all 31 unit tests directly in your terminal to prove 100% compliance:
```bash
python -m pytest tests/ -v
```

### Test Coverage Highlights:
- **`tests/test_auth.py`**: User registration, password length bounds, duplicate email/username rejection, valid JWT generation, invalid credentials rejection.
- **`tests/test_events.py`**: Full CRUD, pagination limits/offsets, title and date filtering, whitespace-only rejection, non-existent event 404.
- **`tests/test_registrations.py`**: Registration creation, duplicate registration 409, capacity ceiling 409, non-existent event/user 404, registration cancellation.

---

## Summary of Status Codes Demonstrated

| Code | Meaning | Where Demonstrated |
|:---:|:---|:---|
| **200** | OK | User login, event listing, single event retrieval, attendee list |
| **201** | Created | User registration, event creation, event signup |
| **204** | No Content | Event deletion, registration cancellation |
| **401** | Unauthorized | Attempting CUD operations without valid JWT token |
| **404** | Not Found | Fetching or registering for non-existent event ID |
| **409** | Conflict | Duplicate username/email, duplicate registration, capacity exceeded |
| **422** | Unprocessable Entity | Blank whitespace title, capacity ≤ 0, invalid username characters |
