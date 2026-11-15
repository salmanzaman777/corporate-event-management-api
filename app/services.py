"""Business logic layer.

All database operations live here. Routes call these functions and nothing else.
Every function is async and uses the SQLAlchemy 2.0 async session API.

JWT is implemented using Python stdlib only (hmac + hashlib + base64).
Password hashing uses hashlib.scrypt — no third-party crypto dependency needed.
"""

import base64
import hashlib
import hmac
import json
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app import models, schemas

# ---------------------------------------------------------------------------
# JWT configuration — read from environment variables
# ---------------------------------------------------------------------------

SECRET_KEY: str = os.getenv("SECRET_KEY", "change-me-in-production-use-a-long-random-string")
ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))


# ---------------------------------------------------------------------------
# Minimal JWT (HS256) — stdlib only
# ---------------------------------------------------------------------------

def _b64url_encode(data: bytes) -> str:
    """URL-safe base64 encode without padding."""
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64url_decode(s: str) -> bytes:
    """URL-safe base64 decode, re-adding padding."""
    padding = 4 - len(s) % 4
    return base64.urlsafe_b64decode(s + "=" * (padding % 4))


def create_access_token(user_id: int, username: str) -> str:
    """Create a signed HS256 JWT containing user identity and expiry."""
    header = _b64url_encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    expire = datetime.now(tz=timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload_data = {"sub": str(user_id), "username": username, "exp": int(expire.timestamp())}
    payload = _b64url_encode(json.dumps(payload_data).encode())
    signing_input = f"{header}.{payload}".encode()
    sig = _b64url_encode(hmac.new(SECRET_KEY.encode(), signing_input, hashlib.sha256).digest())
    return f"{header}.{payload}.{sig}"


def decode_access_token(token: str) -> Optional[dict]:
    """Verify and decode a JWT; return the payload dict or None on any failure."""
    try:
        header_b64, payload_b64, sig_b64 = token.split(".")
    except ValueError:
        return None
    signing_input = f"{header_b64}.{payload_b64}".encode()
    expected_sig = _b64url_encode(hmac.new(SECRET_KEY.encode(), signing_input, hashlib.sha256).digest())
    if not hmac.compare_digest(expected_sig, sig_b64):
        return None
    try:
        data = json.loads(_b64url_decode(payload_b64))
    except (ValueError, KeyError):
        return None
    if data.get("exp", 0) < datetime.now(tz=timezone.utc).timestamp():
        return None
    return data


# ---------------------------------------------------------------------------
# Password hashing — hashlib.scrypt (stdlib, Python 3.6+)
# ---------------------------------------------------------------------------

_SCRYPT_N = 2**14  # CPU/mem cost — fast enough for tests, secure for production
_SCRYPT_R = 8
_SCRYPT_P = 1


def hash_password(plain: str) -> str:
    """Return a salted scrypt hash of *plain* as a hex string prefixed with salt."""
    salt = secrets.token_bytes(16)
    dk = hashlib.scrypt(plain.encode(), salt=salt, n=_SCRYPT_N, r=_SCRYPT_R, p=_SCRYPT_P)
    return salt.hex() + ":" + dk.hex()


def verify_password(plain: str, stored: str) -> bool:
    """Return True if *plain* matches the stored scrypt hash."""
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
    """Register a new user. Raises ValueError on duplicate username/email."""
    existing = await db.scalar(
        select(models.User).where(
            (models.User.username == data.username) | (models.User.email == data.email)
        )
    )
    if existing:
        raise ValueError("Username or email already registered.")

    user = models.User(
        username=data.username,
        email=data.email,
        hashed_password=hash_password(data.password),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def authenticate_user(db: AsyncSession, username: str, password: str) -> Optional[models.User]:
    """Return the User if credentials are valid, else None."""
    user = await db.scalar(select(models.User).where(models.User.username == username))
    if user and verify_password(password, user.hashed_password):
        return user
    return None


async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[models.User]:
    """Fetch a single user by primary key."""
    return await db.get(models.User, user_id)


# ---------------------------------------------------------------------------
# Event services
# ---------------------------------------------------------------------------


async def create_event(db: AsyncSession, data: schemas.EventCreate) -> models.Event:
    """Persist a new event and return it."""
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
    date: Optional[str] = None,
) -> tuple[int, list[models.Event]]:
    """Return (total_count, page) of events, optionally filtered by title/date."""
    query = select(models.Event)

    if title:
        query = query.where(models.Event.title.ilike(f"%{title}%"))

    if date:
        try:
            target = datetime.strptime(date, "%Y-%m-%d").date()
            query = query.where(func.date(models.Event.event_date) == target)
        except ValueError:
            pass  # invalid date string — ignore filter rather than crash

    total: int = await db.scalar(select(func.count()).select_from(query.subquery()))
    result = await db.execute(query.offset(skip).limit(limit))
    return total, list(result.scalars().all())


async def get_event(db: AsyncSession, event_id: int) -> Optional[models.Event]:
    """Fetch a single event by id."""
    return await db.get(models.Event, event_id)


async def update_event(
    db: AsyncSession, event_id: int, data: schemas.EventUpdate
) -> Optional[models.Event]:
    """Apply partial updates to an event. Returns None if not found."""
    event = await db.get(models.Event, event_id)
    if not event:
        return None

    changes = data.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(event, field, value)

    event.updated_at = datetime.now(tz=timezone.utc)
    await db.commit()
    await db.refresh(event)
    return event


async def delete_event(db: AsyncSession, event_id: int) -> bool:
    """Delete an event. Returns True if deleted, False if not found."""
    event = await db.get(models.Event, event_id)
    if not event:
        return False
    await db.delete(event)
    await db.commit()
    return True


# ---------------------------------------------------------------------------
# Registration services
# ---------------------------------------------------------------------------


async def register_for_event(
    db: AsyncSession, event_id: int, user_id: int
) -> models.Registration:
    """Register *user_id* for *event_id*.

    Raises:
        LookupError: event not found.
        LookupError: user not found.
        ValueError: duplicate registration.
        OverflowError: event at capacity.
    """
    event = await db.get(models.Event, event_id)
    if not event:
        raise LookupError(f"Event {event_id} not found.")

    user = await db.get(models.User, user_id)
    if not user:
        raise LookupError(f"User {user_id} not found.")

    # Duplicate check
    duplicate = await db.scalar(
        select(models.Registration).where(
            (models.Registration.event_id == event_id)
            & (models.Registration.user_id == user_id)
        )
    )
    if duplicate:
        raise ValueError(f"User {user_id} is already registered for event {event_id}.")

    # Capacity check
    current_count: int = await db.scalar(
        select(func.count()).where(models.Registration.event_id == event_id)
    )
    if current_count >= event.max_capacity:
        raise OverflowError(f"Event {event_id} has reached its maximum capacity of {event.max_capacity}.")

    registration = models.Registration(event_id=event_id, user_id=user_id)
    db.add(registration)
    await db.commit()
    await db.refresh(registration)
    return registration


async def get_event_registrations(db: AsyncSession, event_id: int) -> list[models.Registration]:
    """Return all registrations for *event_id*. Raises LookupError if event missing."""
    event = await db.get(models.Event, event_id)
    if not event:
        raise LookupError(f"Event {event_id} not found.")

    result = await db.execute(
        select(models.Registration)
        .where(models.Registration.event_id == event_id)
        .options(selectinload(models.Registration.user))
    )
    return list(result.scalars().all())


async def cancel_registration(db: AsyncSession, registration_id: int) -> bool:
    """Cancel a registration by id. Returns True if deleted, False if not found."""
    reg = await db.get(models.Registration, registration_id)
    if not reg:
        return False
    await db.delete(reg)
    await db.commit()
    return True
