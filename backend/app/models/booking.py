import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Booking(Base):
    __tablename__ = "bookings"
    __table_args__ = (
        CheckConstraint(
            "booking_status IN ('pending', 'confirmed', 'cancelled')",
            name="bookings_booking_status_check",
        ),
        CheckConstraint(
            "payment_status IN ('unpaid', 'paid', 'refunded')",
            name="bookings_payment_status_check",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    tour_slot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tour_slots.id"), nullable=False, index=True
    )
    num_participants: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="1"
    )
    booking_status: Mapped[str] = mapped_column(
        String(50), nullable=False, server_default="pending"
    )
    payment_status: Mapped[str] = mapped_column(
        String(50), nullable=False, server_default="unpaid"
    )
    code: Mapped[str | None] = mapped_column(String(8), unique=True)
    payment_session_ref: Mapped[str | None] = mapped_column(String(255))
    payment_intent_ref: Mapped[str | None] = mapped_column(
        String(255), unique=True
    )
    agreed_price_per_participant_cents: Mapped[int] = mapped_column(
        Integer, nullable=False
    )
    total_amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    special_requests: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class BookingParticipant(Base):
    __tablename__ = "booking_participants"
    __table_args__ = (
        UniqueConstraint(
            "booking_id", "participant_id", name="booking_participants_unique"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    booking_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("bookings.id"), nullable=False
    )
    participant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("participants.id"), nullable=False
    )
    is_lead: Mapped[bool | None] = mapped_column(nullable=True)
    attended: Mapped[bool | None] = mapped_column(nullable=True)
    attend_confirmed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id")
    )
    attend_confirmed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
