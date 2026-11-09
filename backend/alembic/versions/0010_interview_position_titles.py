"""Allow practice question sets for positions without a job posting."""

from alembic import op
import sqlalchemy as sa

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("interview_question_sets") as batch:
        batch.alter_column("job_id",existing_type=sa.Integer(),existing_nullable=False,nullable=True)
        batch.add_column(sa.Column("company_id",sa.Integer()))
        batch.add_column(sa.Column("position_title",sa.String(200)))
        batch.create_foreign_key("fk_interview_sets_company","companies",["company_id"],["id"])


def downgrade():
    # The NOT NULL conversion fails if standalone sets still exist.
    with op.batch_alter_table("interview_question_sets") as batch:
        batch.alter_column("job_id",existing_type=sa.Integer(),existing_nullable=True,nullable=False)
        batch.drop_constraint("fk_interview_sets_company",type_="foreignkey")
        batch.drop_column("position_title")
        batch.drop_column("company_id")
