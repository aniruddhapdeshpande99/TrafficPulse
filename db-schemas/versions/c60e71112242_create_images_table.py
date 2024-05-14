"""
create images table

Revision ID: c60e71112242
Revises: 
Create Date: 2023-11-03 09:58:19.041293

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c60e71112242'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'images',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('timestamp', sa.DateTime, nullable=False),
        sa.Column('image', sa.LargeBinary, nullable=False),
        sa.Column('image_url', sa.String(length=200), nullable=False),
        sa.Column('latitude', sa.Float, nullable=False),
        sa.Column('longitude', sa.Float, nullable=False),
        sa.Column('camera_id', sa.String(length=50), nullable=False),
        # Height of the image
        sa.Column('height', sa.Integer, nullable=False),
        # Width of the image
        sa.Column('width', sa.Integer, nullable=False),
        # MD5 of the image
        sa.Column('md5', sa.String(length=32), nullable=False)
    )

    # Create an index on the 'camera_id' and 'timestamp' columns
    op.create_index(op.f('ix_images_camera_id_timestamp'), 'images', ['camera_id', 'timestamp'])

    # Create an index on the 'md5' column
    op.create_index(op.f('ix_images_md5'), 'images', ['md5'])


def downgrade() -> None:
    op.drop_table('images')
