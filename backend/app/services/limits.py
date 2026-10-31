import time
from collections import defaultdict, deque
from threading import Lock
from fastapi import HTTPException
_attempts = defaultdict(deque)
_lock = Lock()
def limit(key: str, count: int, seconds: int):
    now = time.monotonic()
    with _lock:
        hits = _attempts[key]
        while hits and hits[0] <= now - seconds: hits.popleft()
        if len(hits) >= count: raise HTTPException(429, "操作太频繁，请稍后再试")
        hits.append(now)
        if len(_attempts) > 10000:
            for old in list(_attempts):
                if not _attempts[old] or _attempts[old][-1] < now - 3600: del _attempts[old]
