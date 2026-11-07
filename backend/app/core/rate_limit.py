from collections import defaultdict, deque
from threading import Lock
from time import monotonic
from fastapi import HTTPException

_history = defaultdict(deque)
_lock = Lock()

def enforce(key, limit=20, window=60):
    t = monotonic()
    with _lock:
        if len(_history) > 1024:
            for k in list(_history):
                if not _history[k] or _history[k][-1] <= t - 600:
                    del _history[k]
        hits = _history[key]
        while hits and hits[0] <= t - window:
            hits.popleft()
        if len(hits) >= limit:
            raise HTTPException(429, "Bạn thao tác quá nhanh. Hãy thử lại sau ít phút.")
        hits.append(t)
