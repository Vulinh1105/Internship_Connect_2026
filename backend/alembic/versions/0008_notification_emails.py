"""Outbox for optional notification emails."""

from alembic import op
import sqlalchemy as sa

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "notification_emails",
        sa.Column("id",sa.Integer,primary_key=True),
        sa.Column("user_id",sa.Integer,sa.ForeignKey("users.id"),nullable=False),
        sa.Column("message",sa.String(400),nullable=False),
        sa.Column("attempts",sa.Integer,nullable=False),
        sa.Column("available_at",sa.DateTime,nullable=False),
    )


def downgrade():
    op.drop_table("notification_emails")
