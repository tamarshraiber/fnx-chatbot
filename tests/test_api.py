"""The HTTP API: input limits, error codes, rate limit and the streaming format.
The chat service is replaced by fakes, so no LLM or database is used."""
import json

import pytest
from fastapi.testclient import TestClient

from backend.config import MAX_HISTORY_ITEMS, MAX_MESSAGE_CHARS, MAX_QUESTION_CHARS, RATE_LIMIT_REQUESTS
from backend.controllers import chat_controller
from backend.main import app
from backend.models.schemas import ChatAnswer
from backend.services.llm_service import AllProvidersFailed
from backend.utils import rate_limit

client = TestClient(app)  # no "with": the slow start-up (embedding model, database) is skipped

ANSWER = ChatAnswer(answer="תשובה", source_url="https://www.fnx.co.il/a", found=True, source_title="כותרת")


@pytest.fixture
def service(monkeypatch):
    """Fake chat service. Set service.fail to an exception to make it raise; service.seen records the calls."""
    class Service:
        fail: Exception | None = None
        seen: list[tuple] = []

    fake = Service()
    fake.seen = []

    def answer_question(question, history):
        fake.seen.append((question, history))
        if fake.fail:
            raise fake.fail
        return ANSWER

    def stream_answer_question(question, history):
        fake.seen.append((question, history))
        if fake.fail:
            raise fake.fail
        yield {"type": "delta", "text": "תש"}
        yield {"type": "delta", "text": "ובה"}
        yield {"type": "final", **ANSWER.model_dump()}

    monkeypatch.setattr(chat_controller, "answer_question", answer_question)
    monkeypatch.setattr(chat_controller, "stream_answer_question", stream_answer_question)
    return fake


def lines(response):
    return [json.loads(line) for line in response.text.splitlines() if line.strip()]


# --- /health ---

def test_health():
    response = client.get("/health")
    assert response.status_code == 200 and response.json() == {"status": "ok"}


# --- /chat ---

def test_chat_returns_the_answer(service):
    response = client.post("/chat", json={"question": "שלום"})
    assert response.status_code == 200
    assert response.json() == ANSWER.model_dump()


def test_chat_passes_the_history_on(service):
    history = [{"role": "user", "content": "א"}, {"role": "assistant", "content": "ב"}]
    client.post("/chat", json={"question": "שלום", "history": history})
    question, received = service.seen[0]
    assert question == "שלום" and [(m.role, m.content) for m in received] == [("user", "א"), ("assistant", "ב")]


BAD_BODIES = {
    "empty question": {"question": ""},
    "spaces only": {"question": "   "},
    "missing question": {},
    "question too long": {"question": "א" * (MAX_QUESTION_CHARS + 1)},
    "too many history items": {"question": "שלום", "history": [{"role": "user", "content": "x"}] * (MAX_HISTORY_ITEMS + 1)},
    "history message too long": {"question": "שלום", "history": [{"role": "user", "content": "x" * (MAX_MESSAGE_CHARS + 1)}]},
}


@pytest.mark.parametrize("path", ["/chat", "/chat/stream"])
@pytest.mark.parametrize("body", BAD_BODIES.values(), ids=BAD_BODIES.keys())
def test_bad_input_is_rejected_without_calling_the_service(service, path, body):
    assert client.post(path, json=body).status_code == 422
    assert service.seen == []


def test_input_at_the_limits_is_accepted(service):
    body = {"question": "א" * MAX_QUESTION_CHARS, "history": [{"role": "user", "content": "x" * MAX_MESSAGE_CHARS}] * MAX_HISTORY_ITEMS}
    assert client.post("/chat", json=body).status_code == 200


def test_all_llms_down_is_503_with_a_friendly_message(service):
    service.fail = AllProvidersFailed("all down")
    response = client.post("/chat", json={"question": "שלום"})
    assert response.status_code == 503 and response.json()["detail"] == chat_controller.BUSY_MESSAGE


def test_an_unexpected_error_is_500_without_details(service):
    service.fail = ValueError("secret internal detail")
    response = client.post("/chat", json={"question": "שלום"})
    assert response.status_code == 500 and "secret" not in response.text


# --- rate limit ---

def test_the_request_over_the_limit_gets_429(service):
    codes = [client.post("/chat", json={"question": "שלום"}).status_code for _ in range(RATE_LIMIT_REQUESTS + 1)]
    assert codes[:-1] == [200] * RATE_LIMIT_REQUESTS and codes[-1] == 429


def test_the_limit_is_shared_by_chat_and_stream(service):
    for _ in range(RATE_LIMIT_REQUESTS):
        client.post("/chat/stream", json={"question": "שלום"})
    assert client.post("/chat", json={"question": "שלום"}).status_code == 429


def test_the_limit_is_released_after_the_window(service, monkeypatch):
    now = [1000.0]
    monkeypatch.setattr(rate_limit.time, "monotonic", lambda: now[0])
    for _ in range(RATE_LIMIT_REQUESTS):
        assert client.post("/chat", json={"question": "שלום"}).status_code == 200
    assert client.post("/chat", json={"question": "שלום"}).status_code == 429
    now[0] += rate_limit.RATE_LIMIT_WINDOW_SECONDS + 1
    assert client.post("/chat", json={"question": "שלום"}).status_code == 200


def test_invalid_requests_also_count_toward_the_limit(service):
    # So someone cannot spam the server with bad requests for free.
    for _ in range(RATE_LIMIT_REQUESTS):
        assert client.post("/chat", json={"question": ""}).status_code == 422
    assert client.post("/chat", json={"question": "שלום"}).status_code == 429


# --- /chat/stream ---

def test_stream_sends_one_json_event_per_line(service):
    response = client.post("/chat/stream", json={"question": "שלום"})
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/x-ndjson")
    assert response.headers["cache-control"] == "no-cache"
    events = lines(response)
    assert [e["type"] for e in events] == ["delta", "delta", "final"]
    assert "".join(e["text"] for e in events[:2]) == "תשובה"  # Hebrew is not escaped
    assert events[2]["answer"] == "תשובה" and events[2]["source_url"] == ANSWER.source_url


def test_stream_failure_before_the_first_event_is_a_normal_http_error(service):
    service.fail = AllProvidersFailed("all down")
    assert client.post("/chat/stream", json={"question": "שלום"}).status_code == 503
    service.fail = ValueError("bug")
    assert client.post("/chat/stream", json={"question": "שלום"}).status_code == 500


@pytest.mark.parametrize("error, status", [(AllProvidersFailed("down"), 503), (ValueError("bug"), 500)])
def test_stream_failure_after_it_started_becomes_an_error_event(monkeypatch, error, status):
    def broken(question, history):
        yield {"type": "delta", "text": "תש"}
        raise error

    monkeypatch.setattr(chat_controller, "stream_answer_question", broken)
    response = client.post("/chat/stream", json={"question": "שלום"})
    assert response.status_code == 200  # the answer had already started
    assert lines(response) == [{"type": "delta", "text": "תש"}, {"type": "error", "status": status}]


def test_stream_with_no_events_is_an_empty_body(monkeypatch):
    monkeypatch.setattr(chat_controller, "stream_answer_question", lambda question, history: iter([]))
    response = client.post("/chat/stream", json={"question": "שלום"})
    assert response.status_code == 200 and response.text == ""
