"""Track CVs removed from the student's active profile."""

from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("cvs", sa.Column("archived", sa.Boolean(), server_default=sa.false(), nullable=False))


def downgrade():
    op.drop_column("cvs", "archived")
