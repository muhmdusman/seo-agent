"""empty message

Revision ID: 978f74715115
Revises: a80ddacd7ea9
Create Date: 2026-09-12 12:02:25.665328

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '978f74715115'
down_revision: Union[str, Sequence[str], None] = 'a80ddacd7ea9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
