"""add_pickup_service_date_to_rfqs

Revision ID: d92ea31f1082
Revises: c85fd20e9341
Create Date: 2026-08-29 00:03:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd92ea31f1082'
down_revision: Union[str, None] = 'c85fd20e9341'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'rfqs',
        sa.Column('pickup_service_date', sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('rfqs', 'pickup_service_date')
