"""Add btree_gist exclusion constraint on bookings

Revision ID: 002_btree_gist_exclusion_constraint
Revises: 001_initial_schema
Create Date: 2026-11-23 10:05:00.000000

Why: Enforces at the database level that no two 'confirmed' bookings for the
same stylist can overlap in time. The btree_gist extension enables scalar
equality (=) on stylist_id alongside GiST range overlap (&&) on tstzrange.
"""
from typing import Sequence, Union
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '002_btree_gist_exclusion_constraint'
down_revision: Union[str, None] = '001_initial_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Enable btree_gist extension (required for integer equality with GiST)
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist;")

    # 2. Add exclusion constraint preventing overlapping confirmed bookings per stylist
    # tstzrange([start_ts, end_ts)) creates a half-open timestamp range.
    # && tests whether the two ranges overlap.
    # WHERE (status = 'confirmed') ensures cancelled/completed bookings don't block new ones.
    op.execute("""
        ALTER TABLE bookings
        ADD CONSTRAINT no_overlapping_confirmed_bookings
        EXCLUDE USING gist (
            stylist_id WITH =,
            tstzrange(start_ts, end_ts) WITH &&
        )
        WHERE (status = 'confirmed');
    """)


def downgrade() -> None:
    op.execute("ALTER TABLE bookings DROP CONSTRAINT IF EXISTS no_overlapping_confirmed_bookings;")
