import hashlib
import math
import re
import unicodedata
from time import sleep
from fastapi import HTTPException
from app.core.config import AI_BACKEND
from app.ai.usage import call
from .llm import client
from .model_config import DIMENSIONS, EMBEDDING, OPENAI_DIMENSIONS, estimate

def normalize(text):
    return "".join(c for c in unicodedata.normalize("NFD",text.casefold().replace("đ","d")) if not unicodedata.combining(c))

def words(text):
    return [term for term in re.findall(r"[\w+#]+(?:\.[\w+#]+)*",normalize(text)) if len(term)>=2]

def local_vector(text):
    v=[0.0]*DIMENSIONS
    for word in words(text):
        n=int.from_bytes(hashlib.blake2b(word.encode(),digest_size=8).digest(),"big")
        v[n%DIMENSIONS]+=1.0
    length=math.sqrt(sum(x*x for x in v))
    return [x/length for x in v] if length else v

def embed(texts,user_id=None):
    if AI_BACKEND=="local":
        with call(user_id,"embedding","local-hash"):
            return [local_vector(t[:12000]) for t in texts]
    return embed_openai(texts,user_id)


def embed_openai(texts,user_id=None):
    from openai import APIError
    texts=[t[:12000] or " " for t in texts]
    for attempt in range(2):
        try:
            with call(user_id,"embedding",EMBEDDING) as stats:
                response=client().embeddings.create(model=EMBEDDING,input=texts,dimensions=OPENAI_DIMENSIONS)
                stats["tokens_in"]=response.usage.total_tokens
                stats["cost_usd"]=estimate(stats["tokens_in"],0)
                return [x.embedding for x in sorted(response.data,key=lambda x:x.index)]
        except APIError as e:
            if attempt:
                raise HTTPException(503,"Không tạo được vector lúc này") from e
            sleep(0.35)
