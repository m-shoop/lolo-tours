import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

_ALLOWED_STATUSES = {"scheduled", "cancelled", "completed"}


class TourSlotRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tour_id: uuid.UUID
    start_time: datetime
    capacity: int
    price_per_participant_cents: int
    status: str
    notes: str | None
    created_by: uuid.UUID
    created_at: datetime
    updated_at: datetime


class TourSlotCreate(BaseModel):
    tour_id: uuid.UUID
    start_time: datetime
    capacity: int = Field(gt=0)
    # If omitted, the router snapshots the parent tour's current price.
    price_per_participant_cents: int | None = Field(default=None, ge=0)
    notes: str | None = Field(default=None, max_length=500)


class TourSlotUpdate(BaseModel):
    start_time: datetime | None = None
    capacity: int | None = Field(default=None, gt=0)
    price_per_participant_cents: int | None = Field(default=None, ge=0)
    notes: str | None = Field(default=None, max_length=500)
    status: str | None = None

    def validated_status(self) -> str | None:
        if self.status is not None and self.status not in _ALLOWED_STATUSES:
            raise ValueError(
                f"status must be one of {sorted(_ALLOWED_STATUSES)}"
            )
        return self.status
