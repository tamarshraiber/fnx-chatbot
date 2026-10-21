"""Answer generation: the rules that stop the bot from making things up. The LLM is replaced by a fake."""
import pytest

from backend.models.schemas import LLMAnswer
from backend.services import generation_service as gen
from tests.helpers import make_chunk

URL = "https://www.fnx.co.il/a"
CHUNKS = [make_chunk(url=URL, title="ביטוח בריאות | הפניקס")]


def fake_llm(monkeypatch, **fields):
    """Make generate_json return a fixed LLMAnswer. Returns a list that records every call."""
    calls = []

    def fake(system_prompt, prompt, schema):
        calls.append(prompt)
        return LLMAnswer(**{"answerable": True, "answer": "תשובה", "source_url": URL, **fields})

    monkeypatch.setattr(gen, "generate_json", fake)
    return calls


# --- generate_answer ---

def test_no_chunks_does_not_call_the_llm(monkeypatch):
    calls = fake_llm(monkeypatch)
    answer = gen.generate_answer("שאלה", [])
    assert answer.found is False and answer.answer == gen.NOT_ON_WEBSITE and answer.source_url is None
    assert calls == []


def test_not_answerable_gives_the_fixed_reply(monkeypatch):
    fake_llm(monkeypatch, answerable=False)
    assert gen.generate_answer("שאלה", CHUNKS).found is False


def test_empty_answer_gives_the_fixed_reply(monkeypatch):
    fake_llm(monkeypatch, answer="   ")
    assert gen.generate_answer("שאלה", CHUNKS).found is False


def test_invented_url_gives_the_fixed_reply(monkeypatch):
    fake_llm(monkeypatch, source_url="https://www.fnx.co.il/invented")
    assert gen.generate_answer("שאלה", CHUNKS).found is False


def test_good_answer_has_source_and_clean_title(monkeypatch):
    fake_llm(monkeypatch, answer="  תשובה טובה  ")
    answer = gen.generate_answer("שאלה", CHUNKS)
    assert answer.found is True
    assert answer.answer == "תשובה טובה"
    assert answer.source_url == URL
    assert answer.source_title == "ביטוח בריאות"


def test_prompt_contains_chunks_and_question(monkeypatch):
    calls = fake_llm(monkeypatch)
    gen.generate_answer("מה הכיסוי?", CHUNKS)
    assert URL in calls[0] and "מה הכיסוי?" in calls[0]


# --- _clean_title ---

@pytest.mark.parametrize("title, expected", [
    ("ביטוח בריאות | הפניקס", "ביטוח בריאות"),
    ("Health insurance - Phoenix", "Health insurance"),
    ("ביטוח – הפניקס ביטוחים", "ביטוח"),
    ("ביטוח בריאות", "ביטוח בריאות"),  # no site name, unchanged
    ("| הפניקס", None),  # nothing left
    ("", None),
    (None, None),
])
def test_clean_title(title, expected):
    assert gen._clean_title(title) == expected


# --- streaming ---

def fake_stream(monkeypatch, pieces):
    monkeypatch.setattr(gen, "stream_text", lambda system_prompt, prompt: iter(pieces))


def run_stream(chunks=CHUNKS):
    """Returns (all delta text joined, the final event)."""
    events = list(gen.stream_answer("שאלה", chunks))
    assert events[-1]["type"] == "final"
    assert all(event["type"] == "delta" for event in events[:-1])
    return "".join(event["text"] for event in events[:-1]), events[-1]


def test_stream_no_chunks_does_not_call_the_llm(monkeypatch):
    def boom(*args):
        raise AssertionError("LLM was called")
    monkeypatch.setattr(gen, "stream_text", boom)
    text, final = run_stream(chunks=[])
    assert text == "" and final["found"] is False


def test_stream_good_answer_hides_the_source_line(monkeypatch):
    fake_stream(monkeypatch, ["זו תשוב", "ה ארוכה ", "מאוד.\nSOURCE: ", URL])
    text, final = run_stream()
    assert "SOURCE" not in text and URL not in text
    assert text.strip() == "זו תשובה ארוכה מאוד."
    assert final["found"] is True
    assert final["answer"] == "זו תשובה ארוכה מאוד."
    assert final["source_url"] == URL
    assert final["source_title"] == "ביטוח בריאות"


def test_stream_deltas_add_up_to_the_final_answer(monkeypatch):
    fake_stream(monkeypatch, list("תשובה קצרה") + ["\nSOURCE:", " " + URL])
    text, final = run_stream()
    assert text.strip() == final["answer"] == "תשובה קצרה"


def test_stream_not_found_in_one_piece(monkeypatch):
    fake_stream(monkeypatch, ["NOT_FOUND"])
    text, final = run_stream()
    assert text == "" and final["found"] is False and final["answer"] == gen.NOT_ON_WEBSITE


def test_stream_not_found_split_in_pieces_sends_nothing(monkeypatch):
    fake_stream(monkeypatch, ["NOT", "_FO", "UND"])
    text, final = run_stream()
    assert text == "" and final["found"] is False


def test_stream_not_found_with_leading_whitespace(monkeypatch):
    fake_stream(monkeypatch, ["\n  NOT_FOUND\n"])
    _, final = run_stream()
    assert final["found"] is False


def test_stream_wrong_url_keeps_the_answer_without_a_source(monkeypatch):
    fake_stream(monkeypatch, ["תשובה.\nSOURCE: https://example.com/other"])
    _, final = run_stream()
    assert final["found"] is True and final["answer"] == "תשובה." and final["source_url"] is None


def test_stream_missing_source_line_keeps_the_answer(monkeypatch):
    fake_stream(monkeypatch, ["תשובה בלי מקור, ארוכה מספיק."])
    text, final = run_stream()
    assert final["found"] is True and final["source_url"] is None
    # The last few characters are held back (they could be the start of "SOURCE:"). The page replaces the
    # streamed text with the final answer, so the streamed text only has to be the start of it.
    assert final["answer"].startswith(text) and len(text) > 0


def test_stream_url_with_decoration_is_accepted(monkeypatch):
    fake_stream(monkeypatch, [f"תשובה.\nSOURCE: <{URL}>."])
    _, final = run_stream()
    assert final["source_url"] == URL


def test_stream_empty_reply_gives_the_fixed_reply(monkeypatch):
    fake_stream(monkeypatch, [])
    _, final = run_stream()
    assert final["found"] is False


def test_stream_only_a_source_line_gives_the_fixed_reply(monkeypatch):
    fake_stream(monkeypatch, [f"SOURCE: {URL}"])
    _, final = run_stream()
    assert final["found"] is False
