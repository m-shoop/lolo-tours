"""Anonymous booking flow.

POST   /api/bookings              create booking + checkout session
GET    /api/bookings/{code}       confirmation page lookup (code + optional session_id)
POST   /api/bookings/lookup       lookup page (code + email, rate-limited)
PATCH  /api/bookings/{code}       edit participants/special_requests (pending only)
POST   /api/bookings/{code}/cancel  cancel booking (pending+unpaid only)
"""
import asyncio
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app import payments
from app.config import settings
from app.database import get_db
from app.models import (
    Booking,
    BookingParticipant,
    Participant,
    TourSlot,
)
from app.schemas.booking import (
    BookingCancel,
    BookingCreate,
    BookingCreateResponse,
    BookingLookupRequest,
    BookingRead,
    BookingUpdate,
)
from app.services.booking_auth import authorize_email, authorize_session
from app.services.booking_code import generate_booking_code
from app.services.booking_response import (
    PENDING_BOOKING_TTL,
    load_booking_with_participants,
    serialize_booking,
)
from app.services.rate_limit import RateLimiter

router = APIRouter()

_lookup_limiter = RateLimiter(
    max_per_minute=settings.booking_lookup_rate_limit_per_minute
)


def _client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _build_redirect_urls(code: str) -> tuple[str, str]:
    origin = settings.public_site_origin.rstrip("/")
    success = (
        f"{origin}/confirmation"
        f"?code={code}&session_id={{CHECKOUT_SESSION_ID}}"
    )
    cancel = (
        f"{origin}/canceled"
        f"?code={code}&session_id={{CHECKOUT_SESSION_ID}}"
    )
    return success, cancel


@router.post(
    "",
    response_model=BookingCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_booking(
    body: BookingCreate, db: AsyncSession = Depends(get_db)
) -> dict:
    leads = [p for p in body.participants if p.is_lead]
    if len(leads) != 1:
        raise HTTPException(
            status_code=422,
            detail="Exactly one participant must be marked is_lead",
        )
    lead = leads[0]
    if not lead.name or not lead.email:
        raise HTTPException(
            status_code=422,
            detail="Lead participant requires a name and email",
        )

    num_participants = len(body.participants)

    # Transactional capacity check + booking insert. Lock the slot row so two
    # simultaneous bookers can't both succeed when only one seat is left.
    slot = (
        await db.execute(
            select(TourSlot)
            .where(TourSlot.id == body.tour_slot_id)
            .with_for_update()
        )
    ).scalar_one_or_none()
    if slot is None:
        raise HTTPException(status_code=404, detail="Tour slot not found")
    if slot.status != "scheduled":
        raise HTTPException(
            status_code=400, detail="Tour slot is not bookable"
        )
    if slot.start_time <= datetime.now(timezone.utc):
        raise HTTPException(
            status_code=400, detail="Tour slot has already started"
        )

    taken = int(
        (
            await db.execute(
                select(
                    func.coalesce(func.sum(Booking.num_participants), 0)
                ).where(
                    Booking.tour_slot_id == slot.id,
                    Booking.booking_status.in_(("pending", "confirmed")),
                )
            )
        ).scalar_one()
    )
    if slot.capacity - taken < num_participants:
        raise HTTPException(
            status_code=409,
            detail={
                "error": "capacity_exceeded",
                "available": max(slot.capacity - taken, 0),
                "requested": num_participants,
            },
        )

    agreed_price_per_participant_cents = slot.price_per_participant_cents
    total_amount_cents = (
        agreed_price_per_participant_cents * num_participants
    )

    code = await _insert_booking_with_unique_code(
        db,
        slot=slot,
        num_participants=num_participants,
        agreed_price_per_participant_cents=(
            agreed_price_per_participant_cents
        ),
        total_amount_cents=total_amount_cents,
        special_requests=body.special_requests,
    )
    booking = (
        await db.execute(select(Booking).where(Booking.code == code))
    ).scalar_one()

    for p in body.participants:
        participant = Participant(
            name=(p.name or "Guest"),
            email=p.email,
        )
        db.add(participant)
        await db.flush()
        db.add(
            BookingParticipant(
                booking_id=booking.id,
                participant_id=participant.id,
                is_lead=True if p.is_lead else None,
            )
        )

    await db.commit()
    await db.refresh(booking)

    # Outside the transaction: ask the payment provider for a checkout
    # session. If this fails, the booking row stays as pending/unpaid and the
    # TTL job will clean it up.
    success_url, cancel_url = _build_redirect_urls(code)
    try:
        session = payments.create_checkout_session(
            booking_id=str(booking.id),
            booking_code=code,
            amount_cents=total_amount_cents,
            success_url=success_url,
            cancel_url=cancel_url,
        )
    except Exception:
        raise HTTPException(
            status_code=502,
            detail="Payment provider unavailable, please try again",
        )

    booking.payment_session_ref = session["session_ref"]
    booking.payment_intent_ref = session["intent_ref"]
    await db.commit()
    await db.refresh(booking)

    # Shell-mode only: simulate the provider's webhook firing after a brief
    # delay so the confirmation page polling sees the state flip from
    # pending → confirmed without any manual intervention. No effect once a
    # real provider is wired (toggle the flag to false to test cancel flow).
    if settings.payment_shell_auto_success:
        asyncio.create_task(
            payments.fake_payment_succeeded(
                session["intent_ref"],
                settings.payment_shell_auto_success_delay_seconds,
            )
        )

    expires_at = booking.created_at + PENDING_BOOKING_TTL
    return {
        "code": code,
        "redirect_url": session["redirect_url"],
        "expires_at": expires_at,
    }


async def _insert_booking_with_unique_code(
    db: AsyncSession,
    *,
    slot: TourSlot,
    num_participants: int,
    agreed_price_per_participant_cents: int,
    total_amount_cents: int,
    special_requests: str | None,
) -> str:
    """Insert with retry on code collision (≤3 attempts)."""
    last_err: Exception | None = None
    for _ in range(3):
        code = generate_booking_code()
        booking = Booking(
            tour_slot_id=slot.id,
            num_participants=num_participants,
            booking_status="pending",
            payment_status="unpaid",
            code=code,
            agreed_price_per_participant_cents=(
                agreed_price_per_participant_cents
            ),
            total_amount_cents=total_amount_cents,
            special_requests=special_requests,
        )
        db.add(booking)
        try:
            await db.flush()
            return code
        except IntegrityError as e:
            last_err = e
            await db.rollback()
            # On rollback, the slot row lock is released. Re-acquire it.
            await db.execute(
                select(TourSlot)
                .where(TourSlot.id == slot.id)
                .with_for_update()
            )
    raise HTTPException(
        status_code=500, detail="Could not allocate booking code"
    ) from last_err


@router.get("/{code}", response_model=BookingRead)
async def get_booking_by_code(
    code: str,
    session_id: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> dict:
    booking = await load_booking_with_participants(db, code=code)
    if booking is None:
        raise HTTPException(status_code=404, detail="Booking not found")

    # Validate session_id if provided. Mismatch is logged into payment_review
    # but the page still renders — the user is authorized by the code.
    if session_id is not None and not authorize_session(booking, session_id):
        from app.models import PaymentReview

        db.add(
            PaymentReview(
                booking_id=booking.id,
                reason="session_id_mismatch",
                details={
                    "supplied_session_id": session_id,
                    "stored_session_ref": booking.payment_session_ref,
                },
            )
        )
        await db.commit()

    return await serialize_booking(db, booking)


@router.post("/lookup", response_model=BookingRead)
async def lookup_booking(
    body: BookingLookupRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    if not _lookup_limiter.check(_client_ip(request)):
        raise HTTPException(
            status_code=429, detail="Too many lookup attempts, slow down"
        )

    booking = await load_booking_with_participants(db, code=body.code)
    if booking is None:
        raise HTTPException(status_code=404, detail="Booking not found")

    if not await authorize_email(db, booking, body.email):
        # Same response shape as not-found to avoid leaking which codes exist.
        raise HTTPException(status_code=404, detail="Booking not found")

    return await serialize_booking(db, booking)


async def _authorize_mutation(
    db: AsyncSession, booking: Booking, auth
) -> None:
    if auth.email and await authorize_email(db, booking, auth.email):
        return
    if auth.session_id and authorize_session(booking, auth.session_id):
        return
    raise HTTPException(status_code=403, detail="Not authorized")


@router.patch("/{code}", response_model=BookingRead)
async def update_booking(
    code: str, body: BookingUpdate, db: AsyncSession = Depends(get_db)
) -> dict:
    booking = await load_booking_with_participants(db, code=code)
    if booking is None:
        raise HTTPException(status_code=404, detail="Booking not found")
    await _authorize_mutation(db, booking, body.auth)

    if booking.booking_status != "pending":
        raise HTTPException(
            status_code=409,
            detail="Booking is not editable in its current state",
        )

    if body.special_requests is not None:
        booking.special_requests = body.special_requests

    if body.participants:
        for p_update in body.participants:
            participant = (
                await db.execute(
                    select(Participant)
                    .join(
                        BookingParticipant,
                        BookingParticipant.participant_id == Participant.id,
                    )
                    .where(
                        BookingParticipant.booking_id == booking.id,
                        Participant.id == p_update.id,
                    )
                )
            ).scalar_one_or_none()
            if participant is None:
                raise HTTPException(
                    status_code=404,
                    detail=f"Participant {p_update.id} not on this booking",
                )
            if p_update.name is not None:
                participant.name = p_update.name
            if p_update.email is not None:
                participant.email = p_update.email

    await db.commit()
    await db.refresh(booking)
    return await serialize_booking(db, booking)


@router.post("/{code}/cancel", response_model=BookingRead)
async def cancel_booking(
    code: str, body: BookingCancel, db: AsyncSession = Depends(get_db)
) -> dict:
    booking = await load_booking_with_participants(db, code=code)
    if booking is None:
        raise HTTPException(status_code=404, detail="Booking not found")
    await _authorize_mutation(db, booking, body.auth)

    if booking.booking_status == "cancelled":
        # Idempotent.
        return await serialize_booking(db, booking)

    if booking.payment_status != "unpaid":
        raise HTTPException(
            status_code=409,
            detail=(
                "Paid bookings cannot be self-cancelled; please contact us"
            ),
        )

    booking.booking_status = "cancelled"
    await db.commit()
    await db.refresh(booking)
    return await serialize_booking(db, booking)
