import os
from app.core.config import AI_BACKEND

CHAT = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")
REPORT = os.getenv("OPENAI_REPORT_MODEL", CHAT)
EMBEDDING = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
STT = os.getenv("OPENAI_STT_MODEL", "whisper-1")
TTS = os.getenv("OPENAI_TTS_MODEL", "tts-1")
OPENAI_DIMENSIONS = int(os.getenv("EMBEDDING_DIMENSIONS","1536"))
DIMENSIONS = 256 if AI_BACKEND=="local" else OPENAI_DIMENSIONS

def estimate(tokens_in,tokens_out):
    rates=[os.getenv("AI_INPUT_USD_PER_MILLION"),os.getenv("AI_OUTPUT_USD_PER_MILLION")]
    if not all(rates):
        return None
    return (tokens_in*float(rates[0])+tokens_out*float(rates[1]))/1_000_000
