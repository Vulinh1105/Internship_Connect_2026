import json
from app.ai.rag.retrieve import retrieve
from app.ai.vector.client import close
from app.core import metadata
from app.core.config import ROOT
from app.core.database import Session

def main():
    path=ROOT/"data/seed/source/ai/chatbot/evaluation_cases.jsonl"
    cases=[json.loads(line) for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]
    hits_at_five=0
    total=0
    with Session() as db:
        for case in cases:
            query=case.get("question") or case.get("query") or case.get("message")
            expected=case.get("expected_source")
            if not query or not expected or case.get("expected_action")!="cite_document":
                continue
            hits=retrieve(db,None,query)
            total+=1
            hits_at_five+=int(expected in {item["source"] for item in hits})
            print(json.dumps({"query":query,"retrieved":[item["source"] for item in hits],"reference":case},
                             ensure_ascii=False))
    print(json.dumps({"cases_with_source":total,"recall_at_5":hits_at_five/max(1,total)}))
    close()

if __name__=="__main__":
    main()
