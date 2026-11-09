import json
from collections import defaultdict

from sqlalchemy import select

from app.core.config import ROOT
from app.modules.companies.models import Company
from app.modules.jobs.models import Job
from app.modules.jobs.repository import visible
from app.modules.mock_interviews.models import Question, QuestionSet
from app.modules.mock_interviews.schemas import QuestionSetInput
from app.modules.mock_interviews.question_sets import practice_job

DATA = ROOT / "data/seed/source/ai/virtual_interview/company_practice.json"
SEED_MARKER = "seed_interview_questions_v1"


def seed_company_interviews(db, job_codes=None):
    data = json.loads(DATA.read_text(encoding="utf-8"))
    bank = defaultdict(list)
    for question in db.scalars(select(Question).order_by(Question.code)):
        bank[question.role].append({
            "question":question.question,
            "kind":"problem_solving" if question.kind=="behavioral" else "both",
            "difficulty":question.difficulty,
            "criteria":"; ".join(row["criterion"] for row in question.rubric),
        })
    stmt = select(Job,Company.name).join(Company).where(*visible(),practice_job()).order_by(Job.id)
    if job_codes is not None:
        stmt = stmt.where(Job.code.in_(job_codes))
    jobs = db.execute(stmt.with_for_update().execution_options(populate_existing=True)).all()
    existing = set(db.scalars(select(QuestionSet.job_id).where(
        QuestionSet.job_id.in_([job.id for job,_ in jobs])).with_for_update()))
    added = 0
    for job,company in jobs:
        if job.id in existing or job.details.get(SEED_MARKER):
            continue
        role = data["title_roles"].get(job.title.split(" – ",1)[0])
        if not role:
            role = next((name for name in data["roles"] if name.casefold() in job.description.casefold()),None)
        fields = {"title":job.title[:90],"company":company[:80],
                  "skill":job.skills[0][:45] if job.skills else "kỹ năng chính của vị trí"}
        original = bank[role][:3] if role else []
        extra = data["roles"].get(role,[])+data["generic"]
        prompts = extra[:8-len(original)]+data["context"]
        questions = original+[
            {"kind":kind,"difficulty":difficulty,"question":prompt.format(**fields),"criteria":criteria}
            for kind,difficulty,prompt,criteria in prompts
        ]
        payload = QuestionSetInput(job_id=job.id,title="Bộ luyện tập mẫu – "+job.title[:140],
            description="Bộ luyện tập mẫu theo yêu cầu của vị trí. Nội dung dành cho luyện phỏng vấn.",
            published=True,questions=questions)
        assert len(payload.questions)==10
        db.add(QuestionSet(**payload.model_dump()))
        job.details = {**job.details,SEED_MARKER:True}
        added += 1
    db.flush()
    return added
