"""Connect the old chatbot runtime to Internship Connect's SQL and Qdrant."""

import atexit
import json
import logging
import os
from pathlib import Path
from queue import Empty, Queue
import subprocess
from threading import Lock, Thread
from time import monotonic

from fastapi import HTTPException

from app.ai.usage import call
from app.core.config import ROOT

from app.modules.knowledge import service as knowledge

from .generate import extract_locally
from .lists import complete_list, list_heading
from .relevance import NO_DATA_MESSAGE, MINIMUM_WORK_AGE_QUERY, asks_minimum_work_age, best_passage
from .retrieve import retrieve
from app.ai.providers.embedding import words


log = logging.getLogger(__name__)
_lock = Lock()
_process = None
_replies = None


def _read_replies(process, replies):
    try:
        for line in process.stdout:
            replies.put(line)
    finally:
        replies.put(None)


def close():
    global _process, _replies
    if _process is not None:
        if _process.poll() is None:
            _process.terminate()
        _process = None
        _replies = None


atexit.register(close)


def _start(python):
    global _process, _replies
    worker = Path(__file__).with_name("legacy_worker.py")
    env = dict(os.environ, HF_HUB_OFFLINE="1", HF_HUB_DISABLE_TELEMETRY="1",
               LANGSMITH_TRACING="false", LANGCHAIN_TRACING_V2="false",
               PYTHONIOENCODING="utf-8")
    env.pop("OPENAI_API_KEY", None)
    env.setdefault("OMP_NUM_THREADS", "4")
    env.setdefault("MKL_NUM_THREADS", "4")
    _process = subprocess.Popen(
        [str((ROOT / python).resolve()), "-u", str(worker)],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, encoding="utf-8", env=env,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    _replies = Queue()
    Thread(target=_read_replies, args=(_process, _replies), daemon=True).start()


def _send(payload):
    _process.stdin.write(json.dumps(payload, ensure_ascii=False) + "\n")
    _process.stdin.flush()


def _retrieve(db, user_id, query, limit, *, collect_lists=False):
    minimum_age = asks_minimum_work_age(query)
    terms = words(MINIMUM_WORK_AGE_QUERY if minimum_age else query)
    candidates = []
    for chunk in retrieve(db, user_id, query, limit=min(limit, 8)):
        _, passage = best_passage(terms, chunk["text"], minimum_work_age=minimum_age)
        if passage or not minimum_age:
            candidate = {**chunk, "rerank_text": passage or chunk["text"][:900]}
            if collect_lists and (heading := list_heading(query, chunk["text"])):
                positions = range(chunk["position"] + 1, chunk["position"] + 4)
                neighbors = knowledge.chunks_for(db, {chunk["document_id"]}, positions=positions)
                neighbors.sort(key=lambda item: item["position"])
                if result := complete_list(heading, chunk["text"], [item["text"] for item in neighbors]):
                    quote, markers = result
                    candidate.update(text=quote, list_markers=markers)
            candidates.append(candidate)
    return candidates


def _run(python, db, user_id, question, *, initial_chunks=None):
    with _lock:
        try:
            if _process is None or _process.poll() is not None:
                _start(python)
            deadline = monotonic() + 180
            _send({"question": question})
            seen_chunks = {}
            while True:
                reply = _replies.get(timeout=max(0, deadline - monotonic()))
                if reply is None:
                    raise OSError("Legacy RAG process exited")
                event = json.loads(reply)
                if event["type"] == "result":
                    break
                if event["type"] == "evidence":
                    _send(extract_locally(event["query"], event["chunks"]))
                    continue
                if event["type"] != "retrieve":
                    raise ValueError("Unexpected legacy RAG event")
                if initial_chunks is not None and event["query"] == question:
                    chunks, initial_chunks = initial_chunks, None
                else:
                    chunks = _retrieve(db, user_id, event["query"], event["limit"])
                seen_chunks.update({f"{c['document_id']}:{c['position']}": c for c in chunks})
                _send({"chunks": chunks})
        except HTTPException:
            close()
            raise
        except (Empty, OSError, ValueError, KeyError, TypeError) as exc:
            log.warning("Legacy RAG unavailable (%s)", type(exc).__name__)
            close()
            raise HTTPException(503, "Pipeline chatbot cũ chưa sẵn sàng.") from exc

    selected = {}
    for citation in event["citations"]:
        for chunk_id in citation["chunk_ids"]:
            if chunk := seen_chunks.get(chunk_id):
                selected.setdefault(chunk["document_id"], chunk)
    if not selected:
        return {"answer": NO_DATA_MESSAGE, "sources": []}
    return {"answer": event["answer"], "sources": [
        {"number": index, "document_id": ident, "title": chunk["title"], "source": chunk["source"]}
        for index, (ident, chunk) in enumerate(selected.items(), 1)
    ]}


def answer(db, user_id, question, python):
    with call(user_id, "rag_legacy", "bge-reranker-v2-m3"):
        query = MINIMUM_WORK_AGE_QUERY if asks_minimum_work_age(question) else question
        query = " ".join(query.split())
        candidates = _retrieve(db, user_id, query, 8, collect_lists=True)
        for chunk in candidates:
            if markers := chunk.get("list_markers"):
                quote = chunk["text"]
                for offset in reversed(markers):
                    quote = quote[:offset].rstrip() + "\n" + quote[offset:]
                return {"answer": quote, "sources": [{
                    "number": 1, "document_id": chunk["document_id"],
                    "title": chunk["title"], "source": chunk["source"],
                }]}
        if not extract_locally(query, candidates)["evidence"]:
            return {"answer": NO_DATA_MESSAGE, "sources": []}
        return _run(python, db, user_id, query, initial_chunks=candidates)
