"""Run the original LangGraph pipeline with the application's document store."""

import json
import sys
from contextlib import redirect_stdout

from langchain_core.documents import Document

from legacy.graph import build_rag_graph
from legacy.evidence import EvidenceJudgeResult
from legacy.reranking import Reranker
from legacy.validation import format_citations, validate_answer


wire = sys.stdout


def send(message):
    print(json.dumps(message, ensure_ascii=False), file=wire, flush=True)


class StoreRetriever:
    def retrieve(self, query, k):
        send({"type": "retrieve", "query": query, "limit": k})
        reply = json.loads(sys.stdin.readline())
        return [
            Document(page_content=chunk["rerank_text"], metadata={
                "full_text": chunk["text"],
                "source": chunk["title"],
                "document_id": chunk["document_id"],
                "chunk_id": f"{chunk['document_id']}:{chunk['position']}",
            })
            for chunk in reply["chunks"]
        ]


def judge_locally(query, chunks):
    texts = [chunk.metadata["full_text"] for chunk in chunks]
    send({"type": "evidence", "query": query, "chunks": [
        {"text": text, "title": chunk.metadata["source"]} for text, chunk in zip(texts, chunks)
    ]})
    selected = json.loads(sys.stdin.readline()).get("evidence", [])
    indices = []
    for item in selected:
        index = item["source"] - 1
        if 0 <= index < len(chunks) and item["quote"] in texts[index]:
            chunks[index] = chunks[index].model_copy(update={"page_content": item["quote"]})
            indices.append(index)
    return EvidenceJudgeResult(sufficient=bool(indices), supported_indices=indices)


def generate_locally(query, chunks):
    return "\n\n".join(chunk.page_content for chunk in chunks)


def validate_for_web(answer, chunks):
    result = validate_answer(answer, chunks)
    if result.get("valid"):
        result["answer"] = result["answer"].removesuffix(format_citations(result["citations"]))
    return result


def main():
    graph = None
    for line in sys.stdin:
        request = json.loads(line)
        with redirect_stdout(sys.stderr):
            if graph is None:
                graph = build_rag_graph(
                    retriever=StoreRetriever(),
                    reranker=Reranker(),
                    generate_fn=generate_locally,
                    comparison_generate_fn=lambda query, branches: "",
                    comparison_splitter=lambda query: None,
                    evidence_judge=judge_locally,
                    answer_validator=validate_for_web,
                )
            state = graph.invoke({"query": request["question"], "history": []})
        send({"type": "result", "answer": state["answer"],
              "citations": state.get("citations", []), "reason": state.get("refusal_reason")})


if __name__ == "__main__":
    main()
