"""Pydantic schemas for request validation and API responses.

Validation rules:
- Non-blank strings stripped of surrounding whitespace.
- Username constrained to alphanumeric characters and underscores.
- Passwords bounded (8-128 chars) to mitigate hashing DoS.
"""

import re
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


# ---------------------------------------------------------------------------
# User & Auth schemas
# ---------------------------------------------------------------------------


class UserCreate(BaseModel):
    """Registration payload for a new user account."""

    username: str = Field(..., min_length=3, max_length=50, examples=["john_doe"])
    email: EmailStr = Field(..., examples=["john@acmecorp.com"])
    password: str = Field(..., min_length=8, max_length=128, examples=["s3cr3tP@ss"])

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        """Validate username contains alphanumeric characters and underscores only."""
        v = v.strip()
        # Enforce alphanumeric + underscores only
        if not re.match(r"^[a-zA-Z0-9_]+$", v):
            raise ValueError("username may only contain letters, numbers, and underscores")
        return v.lower()


class UserResponse(BaseModel):
    """Public user profile; passwords and hashes are omitted."""

    id: int
    username: str
    email: str
    created_at: datetime

    model_config = {"from_attributes": True}


class LoginRequest(BaseModel):
    """User credentials submitted for JWT access token."""

    username: str = Field(..., min_length=1, max_length=50, examples=["john_doe"])
    password: str = Field(..., min_length=1, max_length=128, examples=["s3cr3tP@ss"])


class TokenResponse(BaseModel):
    """Bearer token response returned upon successful authentication."""

    access_token: str
    token_type: str = "bearer"


# ---------------------------------------------------------------------------
# Event schemas
# ---------------------------------------------------------------------------


class EventCreate(BaseModel):
    """Payload to create a new corporate event."""

    title: str = Field(..., min_length=1, max_length=200, examples=["Python Workshop"])
    description: Optional[str] = Field(None, max_length=2000, examples=["FastAPI deep dive."])
    event_date: datetime = Field(..., examples=["2026-12-01T14:00:00Z"])
    location: str = Field(..., min_length=1, max_length=300, examples=["HQ Conf Room A"])
    max_capacity: int = Field(..., gt=0, le=100000, examples=[50])

    @field_validator("title", "location")
    @classmethod
    def reject_blank_whitespace(cls, v: str) -> str:
        """Reject empty or whitespace-only input and return stripped string."""
        clean = v.strip()
        if not clean:
            raise ValueError("field cannot be empty or whitespace only")
        return clean


class EventUpdate(BaseModel):
    """Optional fields for partial event updates."""

    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    event_date: Optional[datetime] = None
    location: Optional[str] = Field(None, min_length=1, max_length=300)
    max_capacity: Optional[int] = Field(None, gt=0, le=100000)

    @field_validator("title", "location")
    @classmethod
    def reject_blank_whitespace(cls, v: Optional[str]) -> Optional[str]:
        """Reject whitespace-only updates when field is explicitly provided."""
        if v is not None:
            clean = v.strip()
            if not clean:
                raise ValueError("field cannot be empty or whitespace only")
            return clean
        return v


class EventResponse(BaseModel):
    """Full event representation."""

    id: int
    title: str
    description: Optional[str]
    event_date: datetime
    location: str
    max_capacity: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Registration schemas
# ---------------------------------------------------------------------------


class RegistrationCreate(BaseModel):
    """Payload to register an employee for an event."""

    user_id: int = Field(..., gt=0, examples=[1])


class RegistrationResponse(BaseModel):
    """Confirmed registration record."""

    id: int
    event_id: int
    user_id: int
    registered_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Paginated list schema
# ---------------------------------------------------------------------------


class PaginatedEvents(BaseModel):
    """Envelope for paginated event queries."""

    total: int
    skip: int
    limit: int
    items: list[EventResponse]
