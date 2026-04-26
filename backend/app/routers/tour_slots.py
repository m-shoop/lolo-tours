import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import CurrentUser, require_permission
from app.models import Tour, TourSlot
from app.schemas.booking import AvailabilityRead
from app.schemas.tour_slot import TourSlotCreate, TourSlotRead, TourSlotUpdate
from app.services.availability import slot_availability

router = APIRouter()


@router.get("/{slot_id}/availability", response_model=AvailabilityRead)
async def get_slot_availability(
    slot_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Public availability lookup. Informational only — the transactional
    capacity check happens inside POST /api/bookings."""
    slot = (
        await db.execute(select(TourSlot).where(TourSlot.id == slot_id))
    ).scalar_one_or_none()
    if slot is None:
        raise HTTPException(status_code=404, detail="Tour slot not found")
    if slot.status != "scheduled":
        raise HTTPException(
            status_code=400, detail="Tour slot is not bookable"
        )
    return await slot_availability(db, slot)


@router.post(
    "",
    response_model=TourSlotRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_tour_slot(
    body: TourSlotCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("tour-slot:edit")),
) -> TourSlot:
    tour = (
        await db.execute(select(Tour).where(Tour.id == body.tour_id))
    ).scalar_one_or_none()
    if tour is None:
        raise HTTPException(status_code=404, detail="Tour not found")
    if not tour.is_active:
        raise HTTPException(status_code=400, detail="Tour is not active")

    slot = TourSlot(
        tour_id=body.tour_id,
        start_time=body.start_time,
        capacity=body.capacity,
        price_per_participant_cents=(
            body.price_per_participant_cents
            if body.price_per_participant_cents is not None
            else tour.price_per_person
        ),
        notes=body.notes,
        created_by=current_user.user.id,
    )
    db.add(slot)
    await db.commit()
    await db.refresh(slot)
    return slot


@router.patch(
    "/{slot_id}",
    response_model=TourSlotRead,
    dependencies=[Depends(require_permission("tour-slot:edit"))],
)
async def update_tour_slot(
    slot_id: uuid.UUID,
    body: TourSlotUpdate,
    db: AsyncSession = Depends(get_db),
) -> TourSlot:
    try:
        body.validated_status()
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    slot = (
        await db.execute(select(TourSlot).where(TourSlot.id == slot_id))
    ).scalar_one_or_none()
    if slot is None:
        raise HTTPException(status_code=404, detail="Tour slot not found")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(slot, field, value)

    await db.commit()
    await db.refresh(slot)
    return slot
