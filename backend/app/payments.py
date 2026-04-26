"""Payment provider integration boundary.

The owner has not yet selected a payment processor. These shells let the rest
of the booking flow be built and tested. When a provider is chosen (Stripe,
Square, etc.), swap each function body with the real implementation. The
function signatures and return shapes are the integration contract — keep
them stable.
"""
import asyncio
import logging
from typing import Any

logger = logging.getLogger(__name__)


def create_checkout_session(
    booking_id: str,
    booking_code: str,
    amount_cents: int,
    success_url: str,
    cancel_url: str,
) -> dict[str, str]:
    # TODO: real provider integration.
    # Real implementation: hand success_url and cancel_url to the provider
    # AS-IS (with the {CHECKOUT_SESSION_ID} placeholder intact). The provider
    # substitutes the placeholder when redirecting the user.
    #
    # In this shell we bypass the provider entirely: substitute a fake session
    # id into success_url so the browser lands directly on the confirmation
    # page. cancel_url is unused — the shell never simulates cancellation.
    fake_session_ref = f"fake_session_{booking_id}"
    fake_intent_ref = f"fake_intent_{booking_id}"
    redirect_url = success_url.replace(
        "{CHECKOUT_SESSION_ID}", fake_session_ref
    )
    return {
        "redirect_url": redirect_url,
        "session_ref": fake_session_ref,
        "intent_ref": fake_intent_ref,
    }


def verify_webhook_signature(payload: bytes, signature: str) -> bool:
    # TODO: real provider HMAC verification.
    return True


def parse_webhook_event(payload: bytes) -> dict[str, Any]:
    # TODO: real provider parsing.
    # Returns the canonical fields the rest of the app cares about.
    return {
        "type": "payment_intent.succeeded",
        "payment_intent_ref": None,
        "amount_cents": None,
    }


def issue_refund(payment_intent_ref: str) -> bool:
    # TODO: real provider refund call.
    # Returns True on success, False on failure (caller must handle failure).
    return True


async def fake_payment_succeeded(
    payment_intent_ref: str, delay_seconds: float
) -> None:
    """Shell-mode helper: simulate the provider's webhook firing.

    Sleeps for `delay_seconds` (so the confirmation page polling has time
    to display the 'Processing…' state), then runs the same state-mutation
    logic the real webhook handler would. Lets the full happy path be
    exercised end-to-end without a real provider or a manual curl.

    Once a real provider is wired, the booking router stops scheduling this
    and the real provider's webhook drives the transition.
    """
    # Imported lazily to avoid a circular import at module load time
    # (payment_processing imports `payments` for issue_refund).
    from sqlalchemy import select

    from app.database import AsyncSessionLocal
    from app.models import Booking
    from app.services.payment_processing import apply_paid_event

    await asyncio.sleep(delay_seconds)
    try:
        async with AsyncSessionLocal() as db:
            booking = (
                await db.execute(
                    select(Booking).where(
                        Booking.payment_intent_ref == payment_intent_ref
                    )
                )
            ).scalar_one_or_none()
            if booking is None:
                logger.warning(
                    "fake_payment_succeeded: no booking for intent_ref=%s",
                    payment_intent_ref,
                )
                return
            await apply_paid_event(db, booking)
            logger.info(
                "fake_payment_succeeded: booking %s -> %s/%s",
                booking.code,
                booking.booking_status,
                booking.payment_status,
            )
    except Exception:
        logger.exception("fake_payment_succeeded failed")
