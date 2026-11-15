"""FastAPI application entry point.

Registers all routers and runs database table creation on startup.
Routes are thin: they validate input (Pydantic handles that), call the
appropriate service function, and map the result to the correct HTTP response.
"""

from contextlib import asynccontextmanager
from typing import Annotated, Optional

from fastapi import Depends, FastAPI, HTTPException, Query, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app import schemas, services
from app.db import Base, engine, get_db

# ---------------------------------------------------------------------------
# Application lifespan — create tables on startup
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create all database tables if they do not already exist."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(
    title="Corporate Event Management API",
    description=(
        "Internal event system for Acme Corp. "
        "Supports full event CRUD, attendee registration with business-rule enforcement, "
        "JWT authentication, pagination, and search/filtering."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# JWT dependency
# ---------------------------------------------------------------------------

bearer_scheme = HTTPBearer(auto_error=False)

DbDep = Annotated[AsyncSession, Depends(get_db)]


async def get_current_user(
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Security(bearer_scheme)],
    db: DbDep,
):
    """Dependency that extracts and validates the JWT bearer token.

    Raises HTTP 401 when the token is missing or invalid.
    """
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")

    payload = services.decode_access_token(credentials.credentials)
    if payload is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token.")

    user = await services.get_user_by_id(db, int(payload["sub"]))
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found.")
    return user


CurrentUser = Annotated[object, Depends(get_current_user)]

# ---------------------------------------------------------------------------
# Auth routes
# ---------------------------------------------------------------------------


@app.post(
    "/auth/register",
    response_model=schemas.UserResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Auth"],
    summary="Register a new user",
)
async def register(data: schemas.UserCreate, db: DbDep):
    """Create a new user account. Returns the created user (no password)."""
    try:
        return await services.create_user(db, data)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@app.post(
    "/auth/login",
    response_model=schemas.TokenResponse,
    tags=["Auth"],
    summary="Login and obtain a JWT access token",
)
async def login(data: schemas.LoginRequest, db: DbDep):
    """Authenticate with username + password; returns a JWT bearer token."""
    user = await services.authenticate_user(db, data.username, data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
        )
    token = services.create_access_token(user.id, user.username)
    return schemas.TokenResponse(access_token=token)


# ---------------------------------------------------------------------------
# Event routes — GET endpoints are public; CUD requires authentication
# ---------------------------------------------------------------------------


@app.post(
    "/events",
    response_model=schemas.EventResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Events"],
    summary="Create a new event (auth required)",
)
async def create_event(data: schemas.EventCreate, db: DbDep, _: CurrentUser):
    """Create and persist a new event. Requires a valid JWT token."""
    return await services.create_event(db, data)


@app.get(
    "/events",
    response_model=schemas.PaginatedEvents,
    tags=["Events"],
    summary="List all events with optional filtering and pagination",
)
async def list_events(
    db: DbDep,
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(10, ge=1, le=100, description="Maximum records to return"),
    title: Optional[str] = Query(None, description="Filter by title substring"),
    date: Optional[str] = Query(None, description="Filter by date (YYYY-MM-DD)"),
):
    """Public endpoint. Supports pagination via `skip`/`limit` and filtering via `title`/`date`."""
    total, items = await services.get_events(db, skip=skip, limit=limit, title=title, date=date)
    return schemas.PaginatedEvents(total=total, skip=skip, limit=limit, items=items)


@app.get(
    "/events/{event_id}",
    response_model=schemas.EventResponse,
    tags=["Events"],
    summary="Retrieve a specific event by ID",
)
async def get_event(event_id: int, db: DbDep):
    """Public endpoint. Returns 404 if the event does not exist."""
    event = await services.get_event(db, event_id)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Event {event_id} not found.")
    return event


@app.put(
    "/events/{event_id}",
    response_model=schemas.EventResponse,
    tags=["Events"],
    summary="Update an existing event (auth required)",
)
async def update_event(event_id: int, data: schemas.EventUpdate, db: DbDep, _: CurrentUser):
    """Partial update — only the supplied fields are changed. Requires JWT."""
    event = await services.update_event(db, event_id, data)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Event {event_id} not found.")
    return event


@app.delete(
    "/events/{event_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Events"],
    summary="Delete an event (auth required)",
)
async def delete_event(event_id: int, db: DbDep, _: CurrentUser):
    """Permanently delete an event and all its registrations. Requires JWT."""
    deleted = await services.delete_event(db, event_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Event {event_id} not found.")


# ---------------------------------------------------------------------------
# Registration routes
# ---------------------------------------------------------------------------


@app.post(
    "/events/{event_id}/registrations",
    response_model=schemas.RegistrationResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Registrations"],
    summary="Register a user for an event (auth required)",
    responses={
        404: {"description": "Event or user not found"},
        409: {"description": "Duplicate registration or event at capacity"},
    },
)
async def register_for_event(
    event_id: int, data: schemas.RegistrationCreate, db: DbDep, _: CurrentUser
):
    """Register *user_id* for the given event.

    Business rules enforced:
    - 404 if the event or user does not exist.
    - 409 if the user is already registered.
    - 409 if the event has reached its capacity.
    """
    try:
        return await services.register_for_event(db, event_id, data.user_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except (ValueError, OverflowError) as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@app.get(
    "/events/{event_id}/registrations",
    response_model=list[schemas.RegistrationResponse],
    tags=["Registrations"],
    summary="View all registrations for an event",
)
async def get_event_registrations(event_id: int, db: DbDep):
    """Public endpoint. Returns 404 if the event does not exist."""
    try:
        return await services.get_event_registrations(db, event_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@app.delete(
    "/registrations/{registration_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Registrations"],
    summary="Cancel a registration (auth required)",
)
async def cancel_registration(registration_id: int, db: DbDep, _: CurrentUser):
    """Delete a registration by its id. Returns 404 if not found."""
    deleted = await services.cancel_registration(db, registration_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Registration {registration_id} not found.",
        )
