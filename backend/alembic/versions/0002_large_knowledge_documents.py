"""Allow larger knowledge documents in MySQL."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.mysql import MEDIUMTEXT


revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    if op.get_context().dialect.name == "mysql":
        op.alter_column(
            "documents", "content", existing_type=sa.Text(),
            type_=MEDIUMTEXT(), existing_nullable=False,
        )


def downgrade():
    if op.get_context().dialect.name == "mysql":
        op.alter_column(
            "documents", "content", existing_type=MEDIUMTEXT(),
            type_=sa.Text(), existing_nullable=False,
        )
