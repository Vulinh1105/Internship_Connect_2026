"""Store the reason an employer gave when rejecting an application."""

from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("applications", sa.Column("decision_reason", sa.Text(), nullable=True))


def downgrade():
    op.drop_column("applications", "decision_reason")
