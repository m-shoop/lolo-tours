"""Helpers to assemble the BookingRead response payload."""
import uuid
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Booking, BookingParticipant, Participant

PENDING_BOOKING_TTL = timedelta(minutes=30)


async def load_booking_with_participants(
    db: AsyncSession,
    *,
    booking_id: uuid.UUID | None = None,
    code: str | None = None,
) -> Booking | None:
    stmt = select(Booking)
    if booking_id is not None:
        stmt = stmt.where(Booking.id == booking_id)
    elif code is not None:
        stmt = stmt.where(Booking.code == code)
    else:
        return None
    return (await db.execute(stmt)).scalar_one_or_none()


async def serialize_booking(db: AsyncSession, booking: Booking) -> dict:
    parts = (
        await db.execute(
            select(Participant, BookingParticipant.is_lead)
            .join(
                BookingParticipant,
                BookingParticipant.participant_id == Participant.id,
            )
            .where(BookingParticipant.booking_id == booking.id)
            .order_by(BookingParticipant.is_lead.desc().nullslast())
        )
    ).all()

    participants = [
        {
            "id": p.id,
            "name": p.name,
            "email": p.email,
            "is_lead": is_lead,
        }
        for (p, is_lead) in parts
    ]

    expires_at = None
    if booking.booking_status == "pending":
        expires_at = booking.created_at + PENDING_BOOKING_TTL

    return {
        "id": booking.id,
        "code": booking.code,
        "tour_slot_id": booking.tour_slot_id,
        "num_participants": booking.num_participants,
        "booking_status": booking.booking_status,
        "payment_status": booking.payment_status,
        "agreed_price_per_participant_cents": (
            booking.agreed_price_per_participant_cents
        ),
        "total_amount_cents": booking.total_amount_cents,
        "special_requests": booking.special_requests,
        "created_at": booking.created_at,
        "updated_at": booking.updated_at,
        "expires_at": expires_at,
        "participants": participants,
    }
