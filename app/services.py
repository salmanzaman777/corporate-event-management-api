"""Business logic layer.

All database queries and mutations reside here; routes never query the database directly.
Async SQLAlchemy 2.0 with standard library HS256 JWT and scrypt password hashing.
"""

import base64
import hashlib
import hmac
import json
import os
import secrets
from datetime import date as date_type, datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app import models, schemas

# ---------------------------------------------------------------------------
# Security & JWT configuration
# ---------------------------------------------------------------------------

SECRET_KEY: str = os.getenv("SECRET_KEY", "change-me-in-production-use-a-long-random-string")

try:
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
except ValueError:
    ACCESS_TOKEN_EXPIRE_MINUTES = 60  # Fallback to safe 1 hour default


# ---------------------------------------------------------------------------
# Zero-dependency HS256 JWT (Standard Library)
# ---------------------------------------------------------------------------


def _b64url_encode(data: bytes) -> str:
    """URL-safe base64 encode without trailing padding."""
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64url_decode(s: str) -> bytes:
    """URL-safe base64 decode with reconstructed padding."""
    padding = (4 - len(s) % 4) % 4
    return base64.urlsafe_b64decode(s + "=" * padding)


def create_access_token(user_id: int, username: str) -> str:
    """Issue a signed HS256 JWT embedding subject identity and expiration."""
    header = _b64url_encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    expire = datetime.now(tz=timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload_dict = {"sub": str(user_id), "username": username, "exp": int(expire.timestamp())}
    payload = _b64url_encode(json.dumps(payload_dict).encode())
    signing_input = f"{header}.{payload}".encode()
    signature = _b64url_encode(hmac.new(SECRET_KEY.encode(), signing_input, hashlib.sha256).digest())
    return f"{header}.{payload}.{signature}"


def decode_access_token(token: str) -> Optional[dict]:
    """Verify HMAC signature and expiration; return payload dict or None."""
    try:
        header_b64, payload_b64, sig_b64 = token.split(".")
    except (ValueError, AttributeError):
        return None

    # Constant-time signature comparison to eliminate timing attacks
    signing_input = f"{header_b64}.{payload_b64}".encode()
    expected_sig = _b64url_encode(hmac.new(SECRET_KEY.encode(), signing_input, hashlib.sha256).digest())
    if not hmac.compare_digest(expected_sig, sig_b64):
        return None

    try:
        data = json.loads(_b64url_decode(payload_b64))
    except (ValueError, KeyError):
        return None

    # Reject expired tokens
    if data.get("exp", 0) < datetime.now(tz=timezone.utc).timestamp():
        return None

    return data


# ---------------------------------------------------------------------------
# Password hashing — scrypt via hashlib (OWASP recommended)
# ---------------------------------------------------------------------------

_SCRYPT_N = 2**14  # 16384 iterations
_SCRYPT_R = 8
_SCRYPT_P = 1


def hash_password(plain: str) -> str:
    """Generate salted scrypt digest (format: salt_hex:hash_hex)."""
    salt = secrets.token_bytes(16)
    dk = hashlib.scrypt(plain.encode(), salt=salt, n=_SCRYPT_N, r=_SCRYPT_R, p=_SCRYPT_P)
    return f"{salt.hex()}:{dk.hex()}"


def verify_password(plain: str, stored: str) -> bool:
    """Verify password against stored digest using constant-time comparison."""
    try:
        salt_hex, dk_hex = stored.split(":", 1)
        salt = bytes.fromhex(salt_hex)
        dk = hashlib.scrypt(plain.encode(), salt=salt, n=_SCRYPT_N, r=_SCRYPT_R, p=_SCRYPT_P)
        return hmac.compare_digest(dk.hex(), dk_hex)
    except (ValueError, AttributeError):
        return False


# ---------------------------------------------------------------------------
# User services
# ---------------------------------------------------------------------------


async def create_user(db: AsyncSession, data: schemas.UserCreate) -> models.User:
    """Register a new user; enforces case-insensitive username & email uniqueness."""
    normalized_username = data.username.lower().strip()
    normalized_email = data.email.lower().strip()

    existing = await db.scalar(
        select(models.User).where(
            (func.lower(models.User.username) == normalized_username)
            | (func.lower(models.User.email) == normalized_email)
        )
    )
    if existing:
        raise ValueError("Username or email already registered.")

    user = models.User(
        username=normalized_username,
        email=normalized_email,
        hashed_password=hash_password(data.password),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def authenticate_user(db: AsyncSession, username: str, password: str) -> Optional[models.User]:
    """Verify user credentials; returns User or None on bad login."""
    normalized_name = username.lower().strip()
    user = await db.scalar(select(models.User).where(func.lower(models.User.username) == normalized_name))
    if user and verify_password(password, user.hashed_password):
        return user
    return None


async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[models.User]:
    """Retrieve user by primary key."""
    return await db.get(models.User, user_id)


# ---------------------------------------------------------------------------
# Event services
# ---------------------------------------------------------------------------


async def create_event(db: AsyncSession, data: schemas.EventCreate) -> models.Event:
    """Insert and return a newly created event."""
    event = models.Event(**data.model_dump())
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return event


async def get_events(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 10,
    title: Optional[str] = None,
    filter_date: Optional[date_type] = None,
) -> tuple[int, list[models.Event]]:
    """Return total count and paginated list with optional title/date filters."""
    query = select(models.Event)

    # Substring search on event title
    if title:
        query = query.where(models.Event.title.ilike(f"%{title.strip()}%"))

    # Exact calendar date match (ignoring time)
    if filter_date is not None:
        query = query.where(func.date(models.Event.event_date) == filter_date)

    # Query total matching records before applying pagination offset/limit
    total: int = (await db.scalar(select(func.count()).select_from(query.subquery()))) or 0
    result = await db.execute(query.order_by(models.Event.event_date.asc()).offset(skip).limit(limit))
    return total, list(result.scalars().all())


async def get_event(db: AsyncSession, event_id: int) -> Optional[models.Event]:
    """Retrieve single event by ID."""
    return await db.get(models.Event, event_id)


async def update_event(
    db: AsyncSession, event_id: int, data: schemas.EventUpdate
) -> Optional[models.Event]:
    """Apply partial update fields to an existing event."""
    event = await db.get(models.Event, event_id)
    if not event:
        return None

    # Only modify attributes present in the request body
    changes = data.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(event, field, value)

    event.updated_at = datetime.now(tz=timezone.utc)
    await db.commit()
    await db.refresh(event)
    return event


async def delete_event(db: AsyncSession, event_id: int) -> bool:
    """Delete an event and cascade-remove its registrations."""
    event = await db.get(models.Event, event_id)
    if not event:
        return False
    await db.delete(event)
    await db.commit()
    return True


# ---------------------------------------------------------------------------
# Registration services & Business Rules
# ---------------------------------------------------------------------------


async def register_for_event(
    db: AsyncSession, event_id: int, user_id: int
) -> models.Registration:
    """Register user for event while enforcing 3 business rules.

    Enforces:
    1. Event and User must exist (LookupError -> 404).
    2. No duplicate registrations per user per event (ValueError -> 409).
    3. Cannot exceed max capacity (OverflowError -> 409).
    """
    event = await db.get(models.Event, event_id)
    if not event:
        raise LookupError(f"Event {event_id} not found.")

    user = await db.get(models.User, user_id)
    if not user:
        raise LookupError(f"User {user_id} not found.")

    # Business Rule 1: Prevent duplicate registration for the same event
    duplicate = await db.scalar(
        select(models.Registration).where(
            (models.Registration.event_id == event_id)
            & (models.Registration.user_id == user_id)
        )
    )
    if duplicate:
        raise ValueError(f"User {user_id} is already registered for event {event_id}.")

    # Business Rule 2: Enforce capacity ceiling
    current_count: int = (
        await db.scalar(
            select(func.count()).where(models.Registration.event_id == event_id)
        )
    ) or 0
    if current_count >= event.max_capacity:
        raise OverflowError(f"Event {event_id} has reached its maximum capacity of {event.max_capacity}.")

    registration = models.Registration(event_id=event_id, user_id=user_id)
    db.add(registration)
    await db.commit()
    await db.refresh(registration)
    return registration


async def get_event_registrations(db: AsyncSession, event_id: int) -> list[models.Registration]:
    """List all registrations for a valid event, with eagerly loaded user details."""
    event = await db.get(models.Event, event_id)
    if not event:
        raise LookupError(f"Event {event_id} not found.")

    result = await db.execute(
        select(models.Registration)
        .where(models.Registration.event_id == event_id)
        .options(selectinload(models.Registration.user))
        .order_by(models.Registration.registered_at.asc())
    )
    return list(result.scalars().all())


async def cancel_registration(db: AsyncSession, registration_id: int) -> bool:
    """Delete a registration by primary ID."""
    reg = await db.get(models.Registration, registration_id)
    if not reg:
        return False
    await db.delete(reg)
    await db.commit()
    return True
