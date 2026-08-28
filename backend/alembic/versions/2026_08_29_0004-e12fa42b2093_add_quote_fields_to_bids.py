"""add_quote_fields_to_bids

Revision ID: e12fa42b2093
Revises: d92ea31f1082
Create Date: 2026-08-29 00:04:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e12fa42b2093'
down_revision: Union[str, None] = 'd92ea31f1082'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'bids',
        sa.Column('carrier_name', sa.String(length=255), nullable=True),
    )
    op.add_column(
        'bids',
        sa.Column('freight_charges', sa.Numeric(precision=12, scale=2), nullable=True),
    )
    op.add_column(
        'bids',
        sa.Column('origin_charges', sa.Numeric(precision=12, scale=2), nullable=True),
    )
    op.add_column(
        'bids',
        sa.Column('destination_charges', sa.Numeric(precision=12, scale=2), nullable=True),
    )
    op.add_column(
        'bids',
        sa.Column('transit_time', sa.String(length=100), nullable=True),
    )
    op.add_column(
        'bids',
        sa.Column('validity_of_quote', sa.String(length=100), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('bids', 'validity_of_quote')
    op.drop_column('bids', 'transit_time')
    op.drop_column('bids', 'destination_charges')
    op.drop_column('bids', 'origin_charges')
    op.drop_column('bids', 'freight_charges')
    op.drop_column('bids', 'carrier_name')
