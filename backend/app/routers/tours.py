import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models import Tour
from app.schemas.booking import (
    TourSlotWithAvailability,
    TourWithAvailability,
)
from app.schemas.tour import TourCreate, TourRead, TourUpdate
from app.services.availability import (
    tour_slots_with_availability,
    tours_with_availability,
)

router = APIRouter()


@router.get("", response_model=list[TourWithAvailability])
async def list_tours(
    guests: int | None = Query(default=None, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """Public listing — only active tours.

    When ?guests=N is provided, each tour is annotated with
    `has_available_capacity` and `next_available_slot_at` so the Schedule
    page can sort/mute tours that can't fit the requested party.
    """
    return await tours_with_availability(db, guests=guests)

@router.get("/{tour_id}", response_model=TourRead)
async def get_tour(
    tour_id: uuid.UUID, db: AsyncSession = Depends(get_db)
) -> Tour:
    tour = (
        await db.execute(select(Tour).where(Tour.id == tour_id))
    ).scalar_one_or_none()
    if tour is None:
        raise HTTPException(status_code=404, detail="Tour not found")
    return tour


@router.get(
    "/{tour_id}/slots", response_model=list[TourSlotWithAvailability]
)
async def list_tour_slots(
    tour_id: uuid.UUID,
    guests: int | None = Query(default=None, ge=1, le=50),
    from_date: datetime | None = Query(default=None, alias="from"),
    to_date: datetime | None = Query(default=None, alias="to"),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """Upcoming scheduled slots for a tour, with availability.

    Defaults to the next 90 days from now. Filters out slots that can't fit
    the requested party when ?guests is provided.
    """
    tour = (
        await db.execute(select(Tour).where(Tour.id == tour_id))
    ).scalar_one_or_none()
    if tour is None or not tour.is_active:
        raise HTTPException(status_code=404, detail="Tour not found")

    now = datetime.now(timezone.utc)
    start = from_date or now
    end = to_date or (now + timedelta(days=90))
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    if end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)

    return await tour_slots_with_availability(
        db, tour_id=tour_id, guests=guests, from_date=start, to_date=end
    )


@router.post(
    "",
    response_model=TourRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("tour-template:edit"))],
)
async def create_tour(
    body: TourCreate, db: AsyncSession = Depends(get_db)
) -> Tour:
    tour = Tour(**body.model_dump())
    db.add(tour)
    await db.commit()
    await db.refresh(tour)
    return tour


@router.patch(
    "/{tour_id}",
    response_model=TourRead,
    dependencies=[Depends(require_permission("tour-template:edit"))],
)
async def update_tour(
    tour_id: uuid.UUID,
    body: TourUpdate,
    db: AsyncSession = Depends(get_db),
) -> Tour:
    tour = (
        await db.execute(select(Tour).where(Tour.id == tour_id))
    ).scalar_one_or_none()
    if tour is None:
        raise HTTPException(status_code=404, detail="Tour not found")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(tour, field, value)

    await db.commit()
    await db.refresh(tour)
    return tour
