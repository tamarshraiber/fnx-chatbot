"""LLM provider fallback: which provider answers, when one is skipped, and how streaming switches providers.
The real providers are replaced by fake functions, so nothing here uses the network."""
import json
import time

import httpx
import pytest

from backend.models.schemas import LLMAnswer
from backend.services import llm_service as llm

GOOD_JSON = json.dumps({"answerable": True, "answer": "תשובה", "source_url": "https://www.fnx.co.il/a"})


def use_providers(monkeypatch, **functions):
    """Replace the providers by fakes, in the order given. Each fake takes (system_prompt, prompt, schema)."""
    monkeypatch.setattr(llm, "_PROVIDERS", {name: (function, lambda: True) for name, function in functions.items()})
    monkeypatch.setattr(llm, "LLM_PROVIDER_ORDER", list(functions))


def failing(error=None):
    def fail(system_prompt, prompt, schema):
        raise error or RuntimeError("quota")
    return fail


def replying(text):
    calls = []

    def reply(system_prompt, prompt, schema):
        calls.append(prompt)
        return text
    reply.calls = calls
    return reply


# --- generate_text / generate_json ---

def test_first_provider_answers(monkeypatch):
    second = replying("second")
    use_providers(monkeypatch, one=replying("  first  "), two=second)
    assert llm.generate_text("sys", "q") == "first"  # trimmed
    assert second.calls == []


def test_next_provider_answers_when_the_first_fails(monkeypatch):
    use_providers(monkeypatch, one=failing(), two=replying("second"))
    assert llm.generate_text("sys", "q") == "second"


def test_failed_provider_is_skipped_during_cooldown(monkeypatch):
    first = replying("first")
    use_providers(monkeypatch, one=first, two=replying("second"))
    llm._blocked_until["one"] = time.monotonic() + 1000
    assert llm.generate_text("sys", "q") == "second"
    assert first.calls == []


def test_provider_is_tried_again_after_the_cooldown(monkeypatch):
    use_providers(monkeypatch, one=replying("first"), two=replying("second"))
    llm._blocked_until["one"] = time.monotonic() - 1
    assert llm.generate_text("sys", "q") == "first"


def test_failure_starts_a_cooldown_and_success_clears_it(monkeypatch):
    use_providers(monkeypatch, one=failing(), two=replying("second"))
    llm.generate_text("sys", "q")
    assert llm._blocked_until["one"] > time.monotonic()
    assert "two" not in llm._blocked_until


def test_when_all_are_cooling_down_they_are_still_tried(monkeypatch):
    use_providers(monkeypatch, one=replying("first"), two=replying("second"))
    llm._blocked_until["one"] = llm._blocked_until["two"] = time.monotonic() + 1000
    assert llm.generate_text("sys", "q") == "first"
    assert "one" not in llm._blocked_until  # it worked, so the cooldown is cleared


def test_provider_without_a_key_is_skipped(monkeypatch):
    skipped = replying("skipped")
    monkeypatch.setattr(llm, "_PROVIDERS", {
        "one": (skipped, lambda: False),
        "two": (replying("second"), lambda: True),
    })
    monkeypatch.setattr(llm, "LLM_PROVIDER_ORDER", ["one", "two"])
    assert llm.generate_text("sys", "q") == "second"
    assert skipped.calls == []


def test_all_providers_failing_raises(monkeypatch):
    use_providers(monkeypatch, one=failing(), two=failing())
    with pytest.raises(llm.AllProvidersFailed) as info:
        llm.generate_text("sys", "q")
    assert "one" in str(info.value) and "two" in str(info.value)


def test_no_keys_at_all_raises(monkeypatch):
    monkeypatch.setattr(llm, "_PROVIDERS", {"one": (replying("x"), lambda: False)})
    monkeypatch.setattr(llm, "LLM_PROVIDER_ORDER", ["one"])
    with pytest.raises(llm.AllProvidersFailed):
        llm.generate_text("sys", "q")


def test_generate_json_returns_the_validated_object(monkeypatch):
    use_providers(monkeypatch, one=replying(GOOD_JSON))
    result = llm.generate_json("sys", "q", LLMAnswer)
    assert isinstance(result, LLMAnswer) and result.answerable and result.answer == "תשובה"


def test_bad_json_moves_on_without_a_cooldown(monkeypatch):
    use_providers(monkeypatch, one=replying("not json"), two=replying(GOOD_JSON))
    assert llm.generate_json("sys", "q", LLMAnswer).answer == "תשובה"
    assert "one" not in llm._blocked_until


def test_json_of_the_wrong_shape_moves_on(monkeypatch):
    use_providers(monkeypatch, one=replying('{"answer": "missing fields"}'), two=replying(GOOD_JSON))
    assert llm.generate_json("sys", "q", LLMAnswer).answerable is True


def test_bad_json_from_every_provider_raises(monkeypatch):
    use_providers(monkeypatch, one=replying("{}"), two=replying("nope"))
    with pytest.raises(llm.AllProvidersFailed):
        llm.generate_json("sys", "q", LLMAnswer)


# --- the OpenAI-style request (Groq / OpenRouter) ---

class FakeResponse:
    def __init__(self, content="hi"):
        self._content = content

    def raise_for_status(self):
        pass

    def json(self):
        return {"choices": [{"message": {"content": self._content}}]}


def test_openai_style_sends_the_schema_and_reads_the_reply(monkeypatch):
    sent = {}

    def fake_post(url, headers, json, timeout):
        sent.update(url=url, headers=headers, body=json)
        return FakeResponse(GOOD_JSON)

    monkeypatch.setattr(llm.httpx, "post", fake_post)
    text = llm._call_openai_style("https://x/api", "KEY", "model-1", "SYSTEM", "USER", LLMAnswer)
    assert text == GOOD_JSON
    assert sent["headers"] == {"Authorization": "Bearer KEY"}
    assert sent["body"]["model"] == "model-1"
    assert sent["body"]["response_format"] == {"type": "json_object"}
    system_message, user_message = sent["body"]["messages"]
    assert system_message["content"].startswith("SYSTEM") and "answerable" in system_message["content"]
    assert user_message == {"role": "user", "content": "USER"}


def test_openai_style_plain_text_has_no_json_mode(monkeypatch):
    sent = {}
    monkeypatch.setattr(llm.httpx, "post", lambda url, headers, json, timeout: sent.update(body=json) or FakeResponse())
    llm._call_openai_style("https://x/api", "KEY", "m", "SYSTEM", "USER", None)
    assert "response_format" not in sent["body"]
    assert sent["body"]["messages"][0]["content"] == "SYSTEM"


def test_openai_style_empty_content_becomes_empty_string(monkeypatch):
    monkeypatch.setattr(llm.httpx, "post", lambda url, headers, json, timeout: FakeResponse(None))
    assert llm._call_openai_style("https://x/api", "KEY", "m", "S", "U", None) == ""


# --- streaming: switching providers ---

def use_streamers(monkeypatch, **streamers):
    monkeypatch.setattr(llm, "_STREAMERS", streamers)
    monkeypatch.setattr(llm, "_PROVIDERS", {name: (None, lambda: True) for name in streamers})
    monkeypatch.setattr(llm, "LLM_PROVIDER_ORDER", list(streamers))


def pieces(*texts):
    return lambda system_prompt, prompt: iter(texts)


def fails_at_start(system_prompt, prompt):
    raise RuntimeError("overloaded")
    yield  # makes this a generator, like the real streamers


def fails_after_one_piece(system_prompt, prompt):
    yield "start"
    raise RuntimeError("connection lost")


def test_stream_uses_the_first_provider(monkeypatch):
    use_streamers(monkeypatch, one=pieces("a", "b"), two=pieces("x"))
    assert list(llm.stream_text("sys", "q")) == ["a", "b"]


def test_stream_failure_before_the_first_piece_switches_provider(monkeypatch):
    use_streamers(monkeypatch, one=fails_at_start, two=pieces("a", "b"))
    assert list(llm.stream_text("sys", "q")) == ["a", "b"]
    assert "one" in llm._blocked_until


def test_stream_failure_after_the_first_piece_is_raised(monkeypatch):
    use_streamers(monkeypatch, one=fails_after_one_piece, two=pieces("never used"))
    received = []
    with pytest.raises(RuntimeError, match="connection lost"):
        for piece in llm.stream_text("sys", "q"):
            received.append(piece)
    assert received == ["start"]


def test_stream_empty_reply_moves_to_the_next_provider(monkeypatch):
    use_streamers(monkeypatch, one=pieces(), two=pieces("a"))
    assert list(llm.stream_text("sys", "q")) == ["a"]


def test_stream_all_failing_raises(monkeypatch):
    use_streamers(monkeypatch, one=fails_at_start, two=pieces())
    with pytest.raises(llm.AllProvidersFailed):
        list(llm.stream_text("sys", "q"))


# --- streaming: reading the lines a provider sends ---

class FakeStream:
    """Stands in for httpx.stream(...): a context manager with iter_lines()."""

    def __init__(self, lines, status_error=False):
        self.lines = lines
        self.status_error = status_error

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def raise_for_status(self):
        if self.status_error:
            raise httpx.HTTPStatusError("429", request=None, response=httpx.Response(429))

    def iter_lines(self):
        return iter(self.lines)


def data(piece):
    return "data: " + json.dumps({"choices": [{"delta": {"content": piece}}]})


def read_stream(monkeypatch, lines, **options):
    monkeypatch.setattr(llm.httpx, "stream", lambda *args, **kwargs: FakeStream(lines, **options))
    return list(llm._stream_openai_style("https://x/api", "KEY", "m", "S", "U"))


def test_openai_stream_reads_data_lines_until_done(monkeypatch):
    lines = [data("שלום"), "", data(" עולם"), "data: [DONE]", data("ignored")]
    assert read_stream(monkeypatch, lines) == ["שלום", " עולם"]


def test_openai_stream_ignores_comments_bad_json_and_empty_pieces(monkeypatch):
    lines = [
        ": OPENROUTER PROCESSING",
        "data: {broken",
        'data: {"no_choices": 1}',
        'data: {"choices": []}',
        'data: {"choices": [{"delta": {}}]}',
        data(""),
        data("ok"),
        "data: [DONE]",
    ]
    assert read_stream(monkeypatch, lines) == ["ok"]


def test_openai_stream_http_error_is_raised(monkeypatch):
    with pytest.raises(httpx.HTTPStatusError):
        read_stream(monkeypatch, [], status_error=True)
