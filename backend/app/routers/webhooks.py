"""Payment provider webhooks.

The handler is idempotent: state transitions are conditional on current state
(per the design's status table), so retries and duplicate deliveries are
no-ops. Always responds 200 quickly — providers expect fast acknowledgment
and will retry on non-2xx.
"""
import logging

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import payments
from app.database import get_db
from app.models import Booking
from app.services.payment_processing import apply_paid_event

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/payment")
async def payment_webhook(
    request: Request,
    x_provider_signature: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> dict:
    payload = await request.body()
    if not payments.verify_webhook_signature(
        payload, x_provider_signature or ""
    ):
        raise HTTPException(status_code=401, detail="Invalid signature")

    event = payments.parse_webhook_event(payload)
    intent_ref = event.get("payment_intent_ref")

    if event.get("type") != "payment_intent.succeeded":
        return {"received": True, "ignored": True}

    if not intent_ref:
        logger.warning("Webhook event missing payment_intent_ref")
        return {"received": True, "ignored": True}

    booking = (
        await db.execute(
            select(Booking).where(Booking.payment_intent_ref == intent_ref)
        )
    ).scalar_one_or_none()
    if booking is None:
        # Unknown intent — log for manual investigation but don't 500
        # (provider will retry indefinitely and a 500 doesn't help).
        logger.warning(
            "Webhook for unknown payment_intent_ref=%s", intent_ref
        )
        return {"received": True, "ignored": True}

    await apply_paid_event(db, booking)
    return {"received": True}
