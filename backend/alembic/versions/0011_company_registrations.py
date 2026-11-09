"""Company registration review queue."""

from alembic import op
import sqlalchemy as sa

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "company_registrations",
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("tax_code", sa.String(13), nullable=False, unique=True),
        sa.Column("info", sa.JSON(), nullable=False),
        sa.Column("files", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
    )
    op.create_index("ix_company_registrations_status", "company_registrations", ["status"])


def downgrade():
    op.drop_table("company_registrations")
