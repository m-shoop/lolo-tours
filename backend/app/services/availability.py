"""Capacity / availability calculation.

Capacity is computed as:
  tour_slots.capacity - SUM(num_participants WHERE booking_status IN
    ('pending', 'confirmed'))

Pending bookings hold seats; TTL-cancelled bookings free seats automatically
because they drop out of the sum. Cancelled and refunded bookings never count.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Booking, Tour, TourSlot

_HOLDING_STATUSES = ("pending", "confirmed")


async def slot_taken_count(db: AsyncSession, slot_id: uuid.UUID) -> int:
    """Sum of num_participants for bookings that hold seats on this slot."""
    result = await db.execute(
        select(func.coalesce(func.sum(Booking.num_participants), 0)).where(
            Booking.tour_slot_id == slot_id,
            Booking.booking_status.in_(_HOLDING_STATUSES),
        )
    )
    return int(result.scalar_one())


async def slot_availability(
    db: AsyncSession, slot: TourSlot
) -> dict[str, int | uuid.UUID]:
    taken = await slot_taken_count(db, slot.id)
    available = max(slot.capacity - taken, 0)
    return {
        "slot_id": slot.id,
        "capacity": slot.capacity,
        "taken": taken,
        "available": available,
    }


async def tours_with_availability(
    db: AsyncSession, guests: int | None = None
) -> list[dict]:
    """List active tours, optionally annotated with availability for N guests.

    When `guests` is provided, computes per-tour `has_available_capacity` and
    `next_available_slot_at` based on upcoming scheduled slots.
    """
    tours = list(
        (
            await db.execute(
                select(Tour).where(Tour.is_active.is_(True)).order_by(Tour.name)
            )
        )
        .scalars()
        .all()
    )

    if guests is None or guests < 1:
        return [_tour_dict(t) for t in tours]

    now = datetime.now(timezone.utc)

    holding_sum = (
        select(
            Booking.tour_slot_id.label("slot_id"),
            func.coalesce(func.sum(Booking.num_participants), 0).label(
                "taken"
            ),
        )
        .where(Booking.booking_status.in_(_HOLDING_STATUSES))
        .group_by(Booking.tour_slot_id)
        .subquery()
    )

    available_expr = TourSlot.capacity - func.coalesce(holding_sum.c.taken, 0)
    has_room = case(
        (available_expr >= guests, 1), else_=0
    )

    rows = (
        await db.execute(
            select(
                TourSlot.tour_id,
                func.bool_or(has_room.cast(Boolean)).label(
                    "has_available_capacity"
                ),
                func.min(
                    case((available_expr >= guests, TourSlot.start_time))
                ).label("next_available_slot_at"),
            )
            .select_from(TourSlot)
            .outerjoin(holding_sum, holding_sum.c.slot_id == TourSlot.id)
            .where(
                TourSlot.status == "scheduled",
                TourSlot.start_time >= now,
            )
            .group_by(TourSlot.tour_id)
        )
    ).all()

    by_tour = {
        r.tour_id: {
            "has_available_capacity": bool(r.has_available_capacity),
            "next_available_slot_at": r.next_available_slot_at,
        }
        for r in rows
    }
    out = []
    for t in tours:
        d = _tour_dict(t)
        info = by_tour.get(t.id, {})
        d["has_available_capacity"] = info.get(
            "has_available_capacity", False
        )
        d["next_available_slot_at"] = info.get("next_available_slot_at")
        out.append(d)
    return out


def _tour_dict(t: Tour) -> dict:
    return {
        "id": t.id,
        "name": t.name,
        "description": t.description,
        "price_per_person": t.price_per_person,
        "duration_minutes": t.duration_minutes,
        "max_capacity": t.max_capacity,
        "is_active": t.is_active,
    }


async def tour_slots_with_availability(
    db: AsyncSession,
    tour_id: uuid.UUID,
    guests: int | None,
    from_date: datetime,
    to_date: datetime,
) -> list[dict]:
    """Upcoming scheduled slots for a tour with availability computed."""
    holding_sum = (
        select(
            Booking.tour_slot_id.label("slot_id"),
            func.coalesce(func.sum(Booking.num_participants), 0).label(
                "taken"
            ),
        )
        .where(Booking.booking_status.in_(_HOLDING_STATUSES))
        .group_by(Booking.tour_slot_id)
        .subquery()
    )

    rows = (
        await db.execute(
            select(
                TourSlot,
                func.coalesce(holding_sum.c.taken, 0).label("taken"),
            )
            .outerjoin(holding_sum, holding_sum.c.slot_id == TourSlot.id)
            .where(
                TourSlot.tour_id == tour_id,
                TourSlot.status == "scheduled",
                TourSlot.start_time >= from_date,
                TourSlot.start_time < to_date,
            )
            .order_by(TourSlot.start_time)
        )
    ).all()

    out = []
    for slot, taken in rows:
        available = max(slot.capacity - int(taken), 0)
        if guests is not None and available < guests:
            continue
        out.append(
            {
                "id": slot.id,
                "tour_id": slot.tour_id,
                "start_time": slot.start_time,
                "capacity": slot.capacity,
                "taken": int(taken),
                "available": available,
                "price_per_participant_cents": slot.price_per_participant_cents,
                "status": slot.status,
            }
        )
    return out
