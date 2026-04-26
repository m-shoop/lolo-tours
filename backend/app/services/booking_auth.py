"""Authorization for mutations on existing bookings.

Two trust contexts:
  - lookup page: user provided code + email → match against lead participant
  - provider redirect: user came from payment provider with code + session_id
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Booking, BookingParticipant, Participant


async def authorize_email(
    db: AsyncSession, booking: Booking, email: str
) -> bool:
    rows = (
        await db.execute(
            select(Participant.email)
            .join(
                BookingParticipant,
                BookingParticipant.participant_id == Participant.id,
            )
            .where(
                BookingParticipant.booking_id == booking.id,
                BookingParticipant.is_lead.is_(True),
            )
        )
    ).all()
    lead_emails = {(r[0] or "").lower() for r in rows}
    return email.lower() in lead_emails


def authorize_session(booking: Booking, session_id: str) -> bool:
    return (
        booking.payment_session_ref is not None
        and booking.payment_session_ref == session_id
    )
