import re
import time

from backend.config import ANSWER_CACHE_MAX, ANSWER_CACHE_SECONDS

# question key -> (time stored, answer as a dict). Kept in memory, so it is empty again after a restart.
_store: dict[str, tuple[float, dict]] = {}


def _key(question: str) -> str:
    """Same key for 'How do I file a claim?' and 'how do I file a claim' (case, spaces and punctuation ignored)."""
    return " ".join(re.sub(r"[^\w\s]", " ", question.lower()).split())


def get(question: str) -> dict | None:
    """The stored answer for this question, or None if there is none or it is too old."""
    if ANSWER_CACHE_MAX <= 0:
        return None
    key = _key(question)
    entry = _store.get(key)
    if entry is None:
        return None
    stored_at, answer = entry
    if time.monotonic() - stored_at > ANSWER_CACHE_SECONDS:
        _store.pop(key, None)
        return None
    return answer


def put(question: str, answer: dict) -> None:
    """Remember an answer. Only real answers are stored (found=True), never the 'not on the website' reply."""
    if ANSWER_CACHE_MAX <= 0 or not answer.get("found") or not answer.get("answer"):
        return
    key = _key(question)
    _store.pop(key, None)  # so a refreshed answer moves to the end
    _store[key] = (time.monotonic(), answer)
    while len(_store) > ANSWER_CACHE_MAX:
        _store.pop(next(iter(_store)))  # drop the oldest
