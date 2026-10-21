"""Small helpers: the answer cache and the retry wrapper."""
import httpx
import pytest
from google.genai import errors

from backend.utils import answer_cache, retry

ANSWER = {"answer": "תשובה", "source_url": "https://www.fnx.co.il/a", "found": True, "source_title": None}


@pytest.fixture
def clock(monkeypatch):
    """A clock we control. clock[0] is the current time in seconds."""
    now = [1000.0]
    monkeypatch.setattr(answer_cache.time, "monotonic", lambda: now[0])
    return now


# --- answer cache ---

def test_cache_miss_is_none():
    assert answer_cache.get("שאלה") is None


def test_cache_returns_what_was_stored():
    answer_cache.put("שאלה", ANSWER)
    assert answer_cache.get("שאלה") == ANSWER


@pytest.mark.parametrize("other", ["How do I file a claim", "how do i file a claim?", "  HOW  do I  file a claim!! "])
def test_cache_key_ignores_case_spaces_and_punctuation(other):
    answer_cache.put("How do I file a claim?", ANSWER)
    assert answer_cache.get(other) == ANSWER


def test_cache_does_not_mix_up_different_questions():
    answer_cache.put("שאלה אחת", ANSWER)
    assert answer_cache.get("שאלה שתיים") is None


def test_not_found_and_empty_answers_are_not_stored():
    answer_cache.put("a", {**ANSWER, "found": False})
    answer_cache.put("b", {**ANSWER, "answer": ""})
    assert answer_cache.get("a") is None and answer_cache.get("b") is None


def test_entries_expire(clock):
    answer_cache.put("שאלה", ANSWER)
    clock[0] += answer_cache.ANSWER_CACHE_SECONDS - 1
    assert answer_cache.get("שאלה") == ANSWER
    clock[0] += 2
    assert answer_cache.get("שאלה") is None
    assert "שאלה" not in answer_cache._store  # the old entry is removed


def test_the_oldest_entry_is_dropped_at_the_size_limit(monkeypatch):
    monkeypatch.setattr(answer_cache, "ANSWER_CACHE_MAX", 2)
    for question in ["one", "two", "three"]:
        answer_cache.put(question, ANSWER)
    assert answer_cache.get("one") is None
    assert answer_cache.get("two") == ANSWER and answer_cache.get("three") == ANSWER


def test_storing_a_question_again_moves_it_to_the_end(monkeypatch):
    monkeypatch.setattr(answer_cache, "ANSWER_CACHE_MAX", 2)
    answer_cache.put("one", ANSWER)
    answer_cache.put("two", ANSWER)
    answer_cache.put("one", ANSWER)  # refreshed, so "two" is now the oldest
    answer_cache.put("three", ANSWER)
    assert answer_cache.get("two") is None and answer_cache.get("one") == ANSWER


def test_size_zero_turns_the_cache_off(monkeypatch):
    monkeypatch.setattr(answer_cache, "ANSWER_CACHE_MAX", 0)
    answer_cache.put("שאלה", ANSWER)
    assert answer_cache.get("שאלה") is None


# --- retry ---

def http_error(code):
    return httpx.HTTPStatusError(str(code), request=None, response=httpx.Response(code))


@pytest.fixture
def sleeps(monkeypatch):
    """Do not really sleep. Returns the list of waits that were asked for."""
    waits = []
    monkeypatch.setattr(retry.time, "sleep", waits.append)
    monkeypatch.setattr(retry, "RETRY_MAX_ATTEMPTS", 4)
    monkeypatch.setattr(retry, "RETRY_BASE_DELAY_SECONDS", 1.0)
    return waits


def flaky(*results):
    """A function that returns or raises each item of `results` in turn. `.calls` counts the calls."""
    items = list(results)

    def function():
        function.calls += 1
        item = items.pop(0)
        if isinstance(item, Exception):
            raise item
        return item
    function.calls = 0
    return function


def test_success_needs_no_retry(sleeps):
    function = flaky("ok")
    assert retry.call_with_retry(function) == "ok" and function.calls == 1 and sleeps == []


@pytest.mark.parametrize("code", [429, 503])
def test_temporary_errors_are_retried(sleeps, code):
    function = flaky(http_error(code), "ok")
    assert retry.call_with_retry(function) == "ok" and function.calls == 2 and len(sleeps) == 1


def test_gemini_errors_are_retried_too(sleeps):
    function = flaky(errors.APIError(503, {"error": {"message": "overloaded"}}), "ok")
    assert retry.call_with_retry(function) == "ok"


@pytest.mark.parametrize("code", [400, 401, 404, 500])
def test_other_errors_are_raised_at_once(sleeps, code):
    function = flaky(http_error(code), "ok")
    with pytest.raises(httpx.HTTPStatusError):
        retry.call_with_retry(function)
    assert function.calls == 1 and sleeps == []


def test_an_error_that_is_not_an_http_error_is_not_caught(sleeps):
    with pytest.raises(ValueError):
        retry.call_with_retry(flaky(ValueError("bug")))


def test_it_gives_up_after_the_maximum_attempts(sleeps):
    function = flaky(*[http_error(429)] * 10)
    with pytest.raises(httpx.HTTPStatusError):
        retry.call_with_retry(function)
    assert function.calls == 4 and len(sleeps) == 3


def test_the_wait_doubles_each_time(sleeps):
    retry.call_with_retry(flaky(http_error(429), http_error(429), http_error(429), "ok"))
    # base delay 1s: about 1, 2, 4 seconds, plus up to 0.5s of random extra
    for wait, base in zip(sleeps, [1, 2, 4]):
        assert base <= wait <= base + 0.5
