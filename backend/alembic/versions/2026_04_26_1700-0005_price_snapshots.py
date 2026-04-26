"""price snapshots: tour_slots.price_per_participant_cents,
bookings.agreed_price_per_participant_cents

Revision ID: 0005
Revises: 0004
Create Date: 2026-04-26

Adds snapshot price columns so editing a tour or slot price never
retroactively changes what an existing slot or booking is billed at.

Backfill rules:
- tour_slots.price_per_participant_cents is seeded from the parent tour's
  current price_per_person — the only price that ever applied to that slot
  in the pre-snapshot world.
- bookings.agreed_price_per_participant_cents is seeded from
  total_amount_cents / num_participants — what the booking was actually
  billed, which is more truthful than the slot/tour price (those weren't
  snapshotted yet, so they may have changed since).
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "tour_slots",
        sa.Column(
            "price_per_participant_cents", sa.Integer(), nullable=True
        ),
    )
    op.execute(
        "UPDATE tour_slots SET price_per_participant_cents = "
        "(SELECT price_per_person FROM tours "
        "WHERE tours.id = tour_slots.tour_id)"
    )
    op.alter_column(
        "tour_slots", "price_per_participant_cents", nullable=False
    )

    op.add_column(
        "bookings",
        sa.Column(
            "agreed_price_per_participant_cents",
            sa.Integer(),
            nullable=True,
        ),
    )
    op.execute(
        "UPDATE bookings SET agreed_price_per_participant_cents = "
        "ROUND(total_amount_cents::numeric / num_participants)"
    )
    op.alter_column(
        "bookings",
        "agreed_price_per_participant_cents",
        nullable=False,
    )


def downgrade() -> None:
    op.drop_column("bookings", "agreed_price_per_participant_cents")
    op.drop_column("tour_slots", "price_per_participant_cents")
