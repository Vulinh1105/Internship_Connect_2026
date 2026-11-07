from pydantic import BaseModel,Field
from app.ai.providers.llm import structured

class Extract(BaseModel):
    source: int=Field(ge=1)
    quote: str=Field(min_length=8,max_length=600)

class Extracts(BaseModel):
    evidence: list[Extract]=Field(max_length=3)

def answer(user_id,question,chunks):
    if not chunks:
        return {"answer":"Mình chưa tìm thấy thông tin này trong tài liệu.", "sources":[]}
    numbered=[{"source":i,"title":c["title"],"text":c["text"]} for i,c in enumerate(chunks,1)]
    fallback={"evidence":[{"source":1,"quote":chunks[0]["text"][:560]}]} if len(chunks[0]["text"])>=8 else {"evidence":[]}
    result=structured(Extracts,"Chọn đoạn trích NGUYÊN VĂN trực tiếp trả lời câu hỏi. Không đủ bằng chứng thì evidence rỗng.",
                      {"question":question,"sources":numbered},fallback,user_id=user_id,feature="rag_answer")
    if any(e.source>len(chunks) or e.quote not in chunks[e.source-1]["text"] for e in result.evidence):
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
