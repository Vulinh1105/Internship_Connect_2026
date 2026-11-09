from hashlib import sha256
from app.core.config import AI_BACKEND
from app.ai.providers.model_config import EMBEDDING, DIMENSIONS, OPENAI_DIMENSIONS

MATCHING_JOBS = "jobs" if AI_BACKEND=="openai" else "matching_jobs"
KINDS = {"jobs", "cvs", "knowledge", "matching_jobs"}


def dimensions(kind):
    return OPENAI_DIMENSIONS if kind=="matching_jobs" else DIMENSIONS


def collection(kind):
    if kind not in KINDS:
        raise ValueError(kind)
    backend = "openai" if kind=="matching_jobs" else AI_BACKEND
    identity = f"{backend}:{EMBEDDING if backend=='openai' else 'hash-v2'}:{dimensions(kind)}"
    return f"career_{kind}_{sha256(identity.encode()).hexdigest()[:10]}"
