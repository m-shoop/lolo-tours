"""booking workflow: code column, payment refs split, payment_review table

Revision ID: 0004
Revises: 0003
Create Date: 2026-04-26

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "bookings",
        sa.Column("code", sa.String(8), nullable=True),
    )
    op.create_unique_constraint("bookings_code_unique", "bookings", ["code"])

    op.add_column(
        "bookings",
        sa.Column("payment_session_ref", sa.String(255), nullable=True),
    )
    op.add_column(
        "bookings",
        sa.Column("payment_intent_ref", sa.String(255), nullable=True),
    )
    op.execute(
        "UPDATE bookings SET payment_intent_ref = stripe_payment_intent_id "
        "WHERE stripe_payment_intent_id IS NOT NULL"
    )
    op.drop_column("bookings", "stripe_payment_intent_id")
    op.create_unique_constraint(
        "bookings_payment_intent_ref_unique",
        "bookings",
        ["payment_intent_ref"],
    )

    op.create_table(
        "payment_review",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "booking_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("bookings.id"),
            nullable=False,
        ),
        sa.Column("reason", sa.String(64), nullable=False),
        sa.Column(
            "details",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "reason IN ('session_id_mismatch', 'refund_failed', "
            "'webhook_unknown_intent', 'manual_review')",
            name="payment_review_reason_check",
        ),
    )
    op.create_index(
        "ix_payment_review_booking_id", "payment_review", ["booking_id"]
    )
    op.create_index(
        "ix_payment_review_unresolved",
        "payment_review",
        ["created_at"],
        postgresql_where=sa.text("resolved_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index(
        "ix_payment_review_unresolved", table_name="payment_review"
    )
    op.drop_index("ix_payment_review_booking_id", table_name="payment_review")
    op.drop_table("payment_review")

    op.drop_constraint(
        "bookings_payment_intent_ref_unique", "bookings", type_="unique"
    )
    op.add_column(
        "bookings",
        sa.Column("stripe_payment_intent_id", sa.String(255), nullable=True),
    )
    op.execute(
        "UPDATE bookings SET stripe_payment_intent_id = payment_intent_ref "
        "WHERE payment_intent_ref IS NOT NULL"
    )
    op.create_unique_constraint(
        "bookings_stripe_payment_intent_id_key",
        "bookings",
        ["stripe_payment_intent_id"],
    )
    op.drop_column("bookings", "payment_intent_ref")
    op.drop_column("bookings", "payment_session_ref")

    op.drop_constraint("bookings_code_unique", "bookings", type_="unique")
    op.drop_column("bookings", "code")
