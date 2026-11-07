from hashlib import sha256
from app.core.config import AI_BACKEND
from app.ai.providers.model_config import EMBEDDING, DIMENSIONS

KINDS = {"jobs", "cvs", "knowledge"}
def collection(kind):
    if kind not in KINDS:
        raise ValueError(kind)
    identity = f"{AI_BACKEND}:{EMBEDDING if AI_BACKEND=='openai' else 'hash-v2'}:{DIMENSIONS}"
    return f"career_{kind}_{sha256(identity.encode()).hexdigest()[:10]}"
