"""add_unique_constraint_to_bids

Revision ID: b74ec10f8231
Revises: a96ad17e927b
Create Date: 2026-08-29 00:01:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b74ec10f8231'
down_revision: Union[str, None] = 'a96ad17e927b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Safely create composite unique constraint on (auction_id, supplier_id)
    op.create_unique_constraint(
        'uq_bid_auction_supplier',
        'bids',
        ['auction_id', 'supplier_id'],
    )


def downgrade() -> None:
    op.drop_constraint('uq_bid_auction_supplier', 'bids', type_='unique')
