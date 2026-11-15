"""FastAPI application entry point.

Thin route handlers delegating entirely to services.
Provides OpenAPI documentation at /docs and enforces RFC 6750 Bearer authentication.
"""

from contextlib import asynccontextmanager
from datetime import date as date_type
from pathlib import Path as SysPath
from typing import Annotated, Optional

from fastapi import Depends, FastAPI, HTTPException, Path, Query, Security, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app import models, schemas, services
from app.db import Base, engine, get_db

# ---------------------------------------------------------------------------
# Application lifespan — auto-creates database tables on startup
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Ensure database schema tables exist on application startup."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(
    title="Corporate Event Management API",
    description=(
        "Internal REST API for Acme Corp event management. "
        "Enforces attendee capacity, prevents duplicate signups, and provides JWT-protected management endpoints."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# Enable CORS for frontend clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_INDEX = SysPath(__file__).resolve().parent.parent / "static" / "index.html"


@app.get("/", include_in_schema=False)
async def serve_root():
    """Serve modern single-file HTML/JS frontend if available; otherwise redirect info."""
    if STATIC_INDEX.exists():
        return FileResponse(STATIC_INDEX)
    return {"message": "Corporate Event Management API. Visit /docs for OpenAPI documentation."}

# ---------------------------------------------------------------------------
# Authentication dependencies
# ---------------------------------------------------------------------------

bearer_scheme = HTTPBearer(auto_error=False)

DbDep = Annotated[AsyncSession, Depends(get_db)]


async def get_current_user(
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Security(bearer_scheme)],
    db: DbDep,
) -> models.User:
    """Validate Bearer JWT and return current active user.

    Raises HTTP 401 with standard WWW-Authenticate header when missing or invalid.
    """
    unauthorized_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = services.decode_access_token(credentials.credentials)
    if not payload:
        raise unauthorized_exc

    # Safely convert sub claim to integer primary key
    raw_sub = payload.get("sub")
    if not raw_sub or not str(raw_sub).isdigit():
        raise unauthorized_exc

    user = await services.get_user_by_id(db, int(raw_sub))
    if not user:
        raise unauthorized_exc

    return user


CurrentUser = Annotated[models.User, Depends(get_current_user)]

# ---------------------------------------------------------------------------
# Auth routes (Public)
# ---------------------------------------------------------------------------


@app.post(
    "/auth/register",
    response_model=schemas.UserResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Auth"],
    summary="Register a new user account",
)
async def register(data: schemas.UserCreate, db: DbDep):
    """Register an employee account. Raises 409 Conflict if username or email exists."""
    try:
        return await services.create_user(db, data)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@app.post(
    "/auth/login",
    response_model=schemas.TokenResponse,
    tags=["Auth"],
    summary="Authenticate and receive JWT token",
)
async def login(data: schemas.LoginRequest, db: DbDep):
    """Verify credentials and issue a signed Bearer JWT access token."""
    user = await services.authenticate_user(db, data.username, data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = services.create_access_token(user.id, user.username)
    return schemas.TokenResponse(access_token=token)


# ---------------------------------------------------------------------------
# Event routes (Public Read / Authenticated Write)
# ---------------------------------------------------------------------------


@app.post(
    "/events",
    response_model=schemas.EventResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Events"],
    summary="Create a new event (Authenticated)",
)
async def create_event(data: schemas.EventCreate, db: DbDep, _: CurrentUser):
    """Create a new event record. Requires JWT Bearer token."""
    return await services.create_event(db, data)


@app.get(
    "/events",
    response_model=schemas.PaginatedEvents,
    tags=["Events"],
    summary="List events with pagination and filtering",
)
async def list_events(
    db: DbDep,
    skip: int = Query(0, ge=0, description="Records to skip for pagination"),
    limit: int = Query(10, ge=1, le=100, description="Max records to return (1-100)"),
    title: Optional[str] = Query(None, description="Filter by title substring"),
    date: Optional[date_type] = Query(None, description="Filter by event date (YYYY-MM-DD)"),
):
    """Public event catalog with offset pagination and optional title/date search filters."""
    total, items = await services.get_events(db, skip=skip, limit=limit, title=title, filter_date=date)
    return schemas.PaginatedEvents(total=total, skip=skip, limit=limit, items=items)


@app.get(
    "/events/{id}",
    response_model=schemas.EventResponse,
    tags=["Events"],
    summary="Retrieve an event by ID",
)
async def get_event(
    id: int = Path(..., gt=0, description="Positive event ID"),
    db: DbDep = None,
):
    """Public endpoint to fetch detailed event information by primary ID."""
    event = await services.get_event(db, id)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Event {id} not found")
    return event


@app.put(
    "/events/{id}",
    response_model=schemas.EventResponse,
    tags=["Events"],
    summary="Update an existing event (Authenticated)",
)
async def update_event(
    data: schemas.EventUpdate,
    id: int = Path(..., gt=0, description="Positive event ID"),
    db: DbDep = None,
    _: CurrentUser = None,
):
    """Apply partial updates to an event. Requires JWT Bearer token."""
    event = await services.update_event(db, id, data)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Event {id} not found")
    return event


@app.delete(
    "/events/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Events"],
    summary="Delete an event (Authenticated)",
)
async def delete_event(
    id: int = Path(..., gt=0, description="Positive event ID"),
    db: DbDep = None,
    _: CurrentUser = None,
):
    """Permanently remove an event and associated registrations. Requires JWT Bearer token."""
    deleted = await services.delete_event(db, id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Event {id} not found")


# ---------------------------------------------------------------------------
# Registration routes (Business-rule enforced)
# ---------------------------------------------------------------------------


@app.post(
    "/events/{id}/registrations",
    response_model=schemas.RegistrationResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Registrations"],
    summary="Register for an event (Authenticated)",
    responses={
        404: {"description": "Event or user not found"},
        409: {"description": "Duplicate registration or event capacity reached"},
    },
)
async def register_for_event(
    data: schemas.RegistrationCreate,
    id: int = Path(..., gt=0, description="Target event ID"),
    db: DbDep = None,
    _: CurrentUser = None,
):
    """Register user for event. Enforces capacity ceiling and duplicate registration prevention."""
    try:
        return await services.register_for_event(db, id, data.user_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except (ValueError, OverflowError) as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@app.get(
    "/events/{id}/registrations",
    response_model=list[schemas.RegistrationResponse],
    tags=["Registrations"],
    summary="List all registrations for an event",
)
async def get_event_registrations(
    id: int = Path(..., gt=0, description="Target event ID"),
    db: DbDep = None,
):
    """Public endpoint to inspect attendee registrations for a specific event."""
    try:
        return await services.get_event_registrations(db, id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@app.delete(
    "/registrations/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Registrations"],
    summary="Cancel a registration (Authenticated)",
)
async def cancel_registration(
    id: int = Path(..., gt=0, description="Registration ID to cancel"),
    db: DbDep = None,
    _: CurrentUser = None,
):
    """Cancel and delete an event registration. Requires JWT Bearer token."""
    deleted = await services.cancel_registration(db, id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Registration {id} not found",
        )
