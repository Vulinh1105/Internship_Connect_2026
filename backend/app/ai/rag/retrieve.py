from app.ai.providers.embedding import embed,words
from app.ai.vector import client as vectors
from app.modules.knowledge import service as knowledge
from fastapi import HTTPException

def retrieve(db,user_id,question):
    query=set(words(question))
    lexical=knowledge.lexical(db,question,20)
    by_key={(d["document_id"],d["position"]):d for d in lexical}
    rr={k:1/(60+i+1) for i,k in enumerate(by_key)}
    try:
        vector=embed([question],user_id)[0]
        matches=vectors.search("knowledge",vector,limit=20)
        authoritative=knowledge.chunks_for(db,{p.payload["entity_id"] for p in matches})
        actual={(d["document_id"],d["position"]):d for d in authoritative}
        for i,p in enumerate(matches):
            key=(p.payload["entity_id"],p.payload["position"])
            if key in actual:
                by_key[key]=actual[key]
                rr[key]=rr.get(key,0)+1/(60+i+1)
    except HTTPException as exc:
        if exc.status_code==429:
            raise
    except Exception:
        pass
    def rank(k):
        d=by_key[k]
        overlap=len(query.intersection(words(d["title"]+" "+d["text"])))
        return rr[k]+overlap*.008
    ranked=sorted(rr,key=rank,reverse=True)
    return [by_key[k] for k in ranked if len(query.intersection(words(by_key[k]["title"]+" "+by_key[k]["text"])))>=2][:5]
