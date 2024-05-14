"""
Add num_vehicles row in the images table

Revision ID: e4a74f718e4f
Revises: c60e71112242
Create Date: 2023-11-07 13:39:39.797443

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e4a74f718e4f'
down_revision: Union[str, None] = 'c60e71112242'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('images', sa.Column('num_vehicles', sa.Integer()))


def downgrade() -> None:
    op.drop_column('images', 'num_vehicles')
