"""Recruitment metrics, feedback and moderation."""

from alembic import op
import sqlalchemy as sa

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("company_members", sa.Column("manager", sa.Boolean, nullable=False, server_default=sa.false()))
    members = sa.table("company_members", sa.column("id",sa.Integer), sa.column("company_id",sa.Integer),
                       sa.column("manager",sa.Boolean), sa.column("active",sa.Boolean))
    first_ids = (sa.select(sa.func.min(members.c.id).label("id")).where(members.c.active==sa.true())
                 .group_by(members.c.company_id).subquery())
    op.execute(sa.update(members).where(members.c.id.in_(sa.select(first_ids.c.id))).values(manager=True))
    op.create_table(
        "placement_feedback",
        sa.Column("application_id", sa.Integer, sa.ForeignKey("applications.id"), primary_key=True),
        sa.Column("completed_at", sa.DateTime),
        sa.Column("interviewer_rating", sa.Integer),
        sa.Column("interviewer_note", sa.Text),
        sa.Column("student_rating", sa.Integer),
        sa.Column("student_review", sa.Text),
        sa.Column("review_status", sa.String(20)),
    )
    op.create_table(
        "job_metrics",
        sa.Column("job_id", sa.Integer, sa.ForeignKey("jobs.id"), primary_key=True),
        sa.Column("views", sa.Integer, nullable=False, server_default="0"),
    )
    op.create_table(
        "job_reports",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("job_id", sa.Integer, sa.ForeignKey("jobs.id"), nullable=False),
        sa.Column("reporter_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("reason", sa.Text, nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("resolution", sa.Text),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.UniqueConstraint("job_id","reporter_id"),
    )


def downgrade():
    op.drop_table("job_reports")
    op.drop_table("job_metrics")
    op.drop_table("placement_feedback")
    op.drop_column("company_members","manager")
