import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class TourImageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tour_id: uuid.UUID
    image_url: str
    image_alt: str
    sort_order: int
    use_as_thumbnail: bool


class TourImageUpdate(BaseModel):
    image_alt: str | None = Field(default=None, min_length=1, max_length=255)
    sort_order: int | None = Field(default=None, ge=0)
    use_as_thumbnail: bool | None = None


class TourRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None
    price_per_person: int
    duration_minutes: int
    max_capacity: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


class TourCreate(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    description: str | None = Field(default=None, max_length=500)
    price_per_person: int = Field(ge=0, description="price in US cents")
    duration_minutes: int = Field(gt=0)
    max_capacity: int = Field(gt=0)
    is_active: bool = True


class TourUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=50)
    description: str | None = Field(default=None, max_length=500)
    price_per_person: int | None = Field(default=None, ge=0)
    duration_minutes: int | None = Field(default=None, gt=0)
    max_capacity: int | None = Field(default=None, gt=0)
    is_active: bool | None = None
