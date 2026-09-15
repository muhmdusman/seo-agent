"""merge migration heads

Revision ID: 4745c7b2ed2e
Revises: 978f74715115, d3a4b5c6d7e8
Create Date: 2026-09-15 09:59:58.749420

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4745c7b2ed2e'
down_revision: Union[str, Sequence[str], None] = ('978f74715115', 'd3a4b5c6d7e8')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
