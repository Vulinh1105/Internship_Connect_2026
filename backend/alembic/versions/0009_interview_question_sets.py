"""Employer interview question sets and question deadlines."""

from alembic import op
import sqlalchemy as sa

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("interview_sessions",sa.Column("question_deadline",sa.DateTime()))
    op.create_table(
        "interview_question_sets",
        sa.Column("id",sa.Integer,primary_key=True),
        sa.Column("job_id",sa.Integer,sa.ForeignKey("jobs.id"),nullable=False),
        sa.Column("title",sa.String(160),nullable=False),
        sa.Column("description",sa.Text,nullable=False),
        sa.Column("published",sa.Boolean,nullable=False),
        sa.Column("questions",sa.JSON,nullable=False),
    )
    op.create_index("ix_interview_question_sets_job_id","interview_question_sets",["job_id"])


def downgrade():
    op.drop_index("ix_interview_question_sets_job_id",table_name="interview_question_sets")
    op.drop_table("interview_question_sets")
    op.drop_column("interview_sessions","question_deadline")
