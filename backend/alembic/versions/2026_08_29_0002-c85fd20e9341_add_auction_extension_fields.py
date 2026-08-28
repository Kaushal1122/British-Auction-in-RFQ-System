"""add_auction_extension_fields

Revision ID: c85fd20e9341
Revises: b74ec10f8231
Create Date: 2026-08-29 00:02:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c85fd20e9341'
down_revision: Union[str, None] = 'b74ec10f8231'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add British Auction extension configuration columns to auctions table
    op.add_column(
        'auctions',
        sa.Column('forced_bid_close_time', sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        'auctions',
        sa.Column('trigger_window_minutes', sa.Integer(), server_default='10', nullable=False),
    )
    op.add_column(
        'auctions',
        sa.Column('extension_duration_minutes', sa.Integer(), server_default='5', nullable=False),
    )
    op.add_column(
        'auctions',
        sa.Column(
            'extension_trigger',
            sa.Enum('BID_RECEIVED', 'ANY_RANK_CHANGE', 'L1_RANK_CHANGE', name='extension_trigger_enum', native_enum=False),
            server_default='BID_RECEIVED',
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column('auctions', 'extension_trigger')
    op.drop_column('auctions', 'extension_duration_minutes')
    op.drop_column('auctions', 'trigger_window_minutes')
    op.drop_column('auctions', 'forced_bid_close_time')
