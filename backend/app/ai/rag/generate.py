from pydantic import BaseModel,Field
from app.ai.providers.embedding import words
from .relevance import MINIMUM_WORK_AGE_QUERY,asks_minimum_work_age,best_passage,supports_minimum_work_age
from app.ai.providers.llm import structured
from app.core.config import AI_BACKEND
from .evidence import judge_evidence

class Extract(BaseModel):
    source: int=Field(ge=1)
    quote: str=Field(min_length=8,max_length=600)

class Extracts(BaseModel):
    evidence: list[Extract]=Field(max_length=3)

def extract_locally(question,chunks):
    minimum_work_age=asks_minimum_work_age(question)
    query=words(MINIMUM_WORK_AGE_QUERY if minimum_work_age else question)
    passages=[(*best_passage(query,chunk["text"],minimum_work_age=minimum_work_age),number)
              for number,chunk in enumerate(chunks,1)]
    score,quote,source=max(passages,key=lambda passage:passage[0],default=(0,"",0))
    return {"evidence":[{"source":source,"quote":quote}] if score else []}


def answer(user_id,question,chunks):
    if AI_BACKEND=="openai":
        chunks=judge_evidence(user_id,question,chunks)
    if not chunks:
        return {"answer":"Mình chưa tìm thấy thông tin này trong tài liệu.", "sources":[]}
    numbered=[{"source":i,"title":c["title"],"text":c["text"]} for i,c in enumerate(chunks,1)]
    fallback=extract_locally(question,chunks)
    result=structured(Extracts,"Chọn đoạn trích NGUYÊN VĂN trực tiếp trả lời câu hỏi. Không đủ bằng chứng thì evidence rỗng.",
                      {"question":question,"sources":numbered},fallback,user_id=user_id,feature="rag_answer")
    minimum_work_age=asks_minimum_work_age(question)
    if any(e.source>len(chunks) or e.quote not in chunks[e.source-1]["text"]
           or (minimum_work_age and not supports_minimum_work_age(e.quote)) for e in result.evidence):
        result=Extracts.model_validate(fallback)
    sources=[]
    lines=[]
    for e in result.evidence:
        c=chunks[e.source-1]
        lines.append(f"{e.quote} [{e.source}]")
        source={"number":e.source,"title":c["title"],"document_id":c["document_id"],"source":c["source"]}
        if source not in sources:
            sources.append(source)
    return {"answer":"\n\n".join(lines) or "Mình chưa tìm thấy thông tin này trong tài liệu.","sources":sources}
