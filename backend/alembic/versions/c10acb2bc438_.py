"""empty message

Revision ID: c10acb2bc438
Revises: 1431de92262d
Create Date: 2026-08-30 16:39:44.334994

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c10acb2bc438'
down_revision: Union[str, Sequence[str], None] = '1431de92262d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
