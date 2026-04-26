"""Background job: cancel pending bookings whose 30-minute TTL has elapsed.

Idempotent conditional UPDATE — safe to run concurrently or repeatedly.
Started from app.main.lifespan; stops when the app shuts down.
"""
import asyncio
import logging

from sqlalchemy import text

from app.config import settings
from app.database import AsyncSessionLocal

logger = logging.getLogger(__name__)


async def sweep_expired_bookings() -> int:
    """Cancel pending bookings older than the configured TTL."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            text(
                "UPDATE bookings "
                "SET booking_status = 'cancelled', updated_at = NOW() "
                "WHERE booking_status = 'pending' "
                "AND created_at < NOW() - make_interval(mins => :ttl_min)"
            ),
            {"ttl_min": settings.booking_ttl_minutes},
        )
        await db.commit()
        return result.rowcount or 0


async def ttl_loop(stop_event: asyncio.Event) -> None:
    interval = settings.booking_ttl_sweep_interval_seconds
    logger.info(
        "Booking TTL sweeper started: interval=%ss ttl=%smin",
        interval,
        settings.booking_ttl_minutes,
    )
    while not stop_event.is_set():
        try:
            cancelled = await sweep_expired_bookings()
            if cancelled:
                logger.info("TTL swept %d expired pending bookings", cancelled)
        except Exception:
            logger.exception("TTL sweep failed")
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=interval)
        except asyncio.TimeoutError:
            pass
    logger.info("Booking TTL sweeper stopped")
