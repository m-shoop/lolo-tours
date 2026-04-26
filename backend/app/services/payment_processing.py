"""State transitions triggered by payment events.

Shared between the real payment webhook handler and the shell-mode
auto-success simulator. Idempotent: every transition checks current state
first, so duplicate or out-of-order calls are no-ops.
"""
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app import payments
from app.models import Booking, PaymentReview

logger = logging.getLogger(__name__)


async def apply_paid_event(db: AsyncSession, booking: Booking) -> None:
    """Apply 'payment succeeded' to a booking per the SHO-96 status table."""
    if booking.payment_status in ("paid", "refunded"):
        return  # idempotent no-op

    if booking.booking_status == "pending":
        booking.payment_status = "paid"
        booking.booking_status = "confirmed"
        await db.commit()
        return

    if booking.booking_status == "confirmed":
        # confirmed/unpaid should be unreachable; treat defensively.
        logger.error(
            "Unreachable state: booking %s confirmed/unpaid received paid "
            "webhook",
            booking.id,
        )
        booking.payment_status = "paid"
        await db.commit()
        return

    if booking.booking_status == "cancelled":
        # Race: TTL or user cancelled, then payment landed. Auto-refund.
        ok = False
        try:
            ok = payments.issue_refund(booking.payment_intent_ref or "")
        except Exception:
            ok = False
        if ok:
            booking.payment_status = "refunded"
            await db.commit()
        else:
            db.add(
                PaymentReview(
                    booking_id=booking.id,
                    reason="refund_failed",
                    details={
                        "payment_intent_ref": booking.payment_intent_ref,
                        "note": (
                            "Cancelled booking received paid webhook; "
                            "automatic refund call failed"
                        ),
                    },
                )
            )
            await db.commit()
        return
