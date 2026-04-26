"""tour_images table and price_per_person -> cents

Revision ID: 0003
Revises: 0002
Create Date: 2026-04-25

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "tours",
        "price_per_person",
        type_=sa.Integer(),
        existing_type=sa.Numeric(10, 2),
        existing_nullable=False,
        postgresql_using="(price_per_person * 100)::integer",
    )

    op.create_table(
        "tour_images",
        sa.Column("id", sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column(
            "tour_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tours.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("image_url", sa.String(255), nullable=False),
        sa.Column("image_alt", sa.String(255), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "use_as_thumbnail",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("FALSE"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_tour_images_tour_id", "tour_images", ["tour_id"])


def downgrade() -> None:
    op.drop_index("ix_tour_images_tour_id", table_name="tour_images")
    op.drop_table("tour_images")

    op.alter_column(
        "tours",
        "price_per_person",
        type_=sa.Numeric(10, 2),
        existing_type=sa.Integer(),
        existing_nullable=False,
        postgresql_using="(price_per_person::numeric / 100)",
    )
