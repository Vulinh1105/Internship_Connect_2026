from fastapi import HTTPException
from app.ai.usage import call
from app.core.config import AI_BACKEND
from .llm import client
from .model_config import STT,TTS

def transcribe(user_id,name,data):
    if AI_BACKEND!="openai":
        raise HTTPException(503,"Chế độ local hỗ trợ nhận giọng nói trên trình duyệt hoặc nhập chữ")
    from openai import APIError
    try:
        with call(user_id,"stt",STT):
            return client().audio.transcriptions.create(model=STT,file=(name,data)).text
    except APIError as e:
        raise HTTPException(503,"Không nhận diện được. Vui lòng nhập chữ.") from e

def speak(user_id,text):
    if AI_BACKEND!="openai":
        raise HTTPException(503,"Dùng chức năng đọc câu hỏi của trình duyệt")
    from openai import APIError
    try:
        with call(user_id,"tts",TTS):
            return client().audio.speech.create(model=TTS,voice="alloy",input=text[:2000]).read()
    except APIError as e:
        raise HTTPException(503,"Không đọc được câu hỏi") from e
