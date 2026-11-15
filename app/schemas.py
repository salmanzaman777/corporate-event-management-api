"""Pydantic schemas for request validation and API responses.

Each domain has three schema variants:
- Create   — fields accepted when creating a resource (no id/timestamps)
- Update   — all fields optional, for PATCH-style partial updates via PUT
- Response — the shape returned to the client
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


# ---------------------------------------------------------------------------
# User schemas
# ---------------------------------------------------------------------------


class UserCreate(BaseModel):
    """Fields required to register a new user."""

    username: str = Field(..., min_length=3, max_length=50, examples=["john_doe"])
    email: EmailStr = Field(..., examples=["john@acmecorp.com"])
    password: str = Field(..., min_length=8, examples=["s3cr3tP@ss"])


class UserResponse(BaseModel):
    """Public user representation (no password exposed)."""

    id: int
    username: str
    email: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Auth schemas
# ---------------------------------------------------------------------------


class LoginRequest(BaseModel):
    """Credentials submitted to obtain a JWT token."""

    username: str = Field(..., examples=["john_doe"])
    password: str = Field(..., examples=["s3cr3tP@ss"])


class TokenResponse(BaseModel):
    """JWT access token returned after successful login."""

    access_token: str
    token_type: str = "bearer"


# ---------------------------------------------------------------------------
# Event schemas
# ---------------------------------------------------------------------------


class EventCreate(BaseModel):
    """Payload for creating a new event."""

    title: str = Field(..., min_length=1, max_length=200, examples=["Python Workshop"])
    description: Optional[str] = Field(None, examples=["Hands-on intro to FastAPI."])
    event_date: datetime = Field(..., examples=["2026-12-01T14:00:00Z"])
    location: str = Field(..., min_length=1, max_length=300, examples=["HQ Conference Room A"])
    max_capacity: int = Field(..., gt=0, examples=[50])

    @field_validator("title")
    @classmethod
    def title_not_blank(cls, v: str) -> str:
        """Reject titles that are only whitespace."""
        if not v.strip():
            raise ValueError("title must not be blank")
        return v.strip()


class EventUpdate(BaseModel):
    """All fields are optional; only supplied fields are changed."""

    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    event_date: Optional[datetime] = None
    location: Optional[str] = Field(None, min_length=1, max_length=300)
    max_capacity: Optional[int] = Field(None, gt=0)

    @field_validator("title")
    @classmethod
    def title_not_blank(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.strip():
            raise ValueError("title must not be blank")
        return v.strip() if v else v


class EventResponse(BaseModel):
    """Full event representation including server-generated fields."""

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
    """Payload to register a user for an event."""

    user_id: int = Field(..., gt=0, examples=[1])


class RegistrationResponse(BaseModel):
    """Registration record returned to the client."""

    id: int
    event_id: int
    user_id: int
    registered_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Shared / utility schemas
# ---------------------------------------------------------------------------


class PaginatedEvents(BaseModel):
    """Paginated list of events with total count."""

    total: int
    skip: int
    limit: int
    items: list[EventResponse]
