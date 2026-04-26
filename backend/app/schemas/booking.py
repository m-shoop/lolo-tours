import uuid
from datetime import datetime
from typing import Literal

import re

from pydantic import BaseModel, ConfigDict, Field, field_validator

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _validate_email(v: str | None) -> str | None:
    if v is None:
        return v
    if not _EMAIL_RE.match(v):
        raise ValueError("invalid email address")
    return v.lower()


class ParticipantInput(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    email: str | None = None
    is_lead: bool = False

    _v_email = field_validator("email")(lambda cls, v: _validate_email(v))


class BookingCreate(BaseModel):
    tour_slot_id: uuid.UUID
    participants: list[ParticipantInput] = Field(min_length=1, max_length=50)
    special_requests: str | None = Field(default=None, max_length=2000)


class ParticipantRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    email: str | None
    is_lead: bool | None


class BookingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    tour_slot_id: uuid.UUID
    num_participants: int
    booking_status: str
    payment_status: str
    agreed_price_per_participant_cents: int
    total_amount_cents: int
    special_requests: str | None
    created_at: datetime
    updated_at: datetime
    expires_at: datetime | None
    participants: list[ParticipantRead] = []


class BookingCreateResponse(BaseModel):
    code: str
    redirect_url: str
    expires_at: datetime


class BookingLookupRequest(BaseModel):
    code: str = Field(min_length=8, max_length=8)
    email: str

    _v_email = field_validator("email")(lambda cls, v: _validate_email(v))


class ParticipantUpdate(BaseModel):
    id: uuid.UUID
    name: str | None = Field(default=None, max_length=255)
    email: str | None = None

    _v_email = field_validator("email")(lambda cls, v: _validate_email(v))


class BookingAuth(BaseModel):
    """Either email or session_id must be provided to authorize a mutation."""

    email: str | None = None
    session_id: str | None = None

    _v_email = field_validator("email")(lambda cls, v: _validate_email(v))


class BookingUpdate(BaseModel):
    auth: BookingAuth
    participants: list[ParticipantUpdate] | None = None
    special_requests: str | None = Field(default=None, max_length=2000)


class BookingCancel(BaseModel):
    auth: BookingAuth


class AvailabilityRead(BaseModel):
    slot_id: uuid.UUID
    capacity: int
    taken: int
    available: int


class TourSlotWithAvailability(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tour_id: uuid.UUID
    start_time: datetime
    capacity: int
    taken: int
    available: int
    price_per_participant_cents: int
    status: str


class TourWithAvailability(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None
    price_per_person: int
    duration_minutes: int
    max_capacity: int
    is_active: bool
    has_available_capacity: bool | None = None
    next_available_slot_at: datetime | None = None


WebhookEventType = Literal[
    "payment_intent.succeeded",
    "payment_intent.payment_failed",
    "checkout.session.completed",
]
