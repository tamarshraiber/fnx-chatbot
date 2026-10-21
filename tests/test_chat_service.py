"""Chat flow: thank-you shortcut, follow-up rewrite, history limit and the answer cache.
Retrieval, generation and the LLM are replaced by fakes."""
import pytest

from backend.models.schemas import ChatAnswer, ChatMessage
from backend.services import chat_service as chat
from backend.services.retrieval_service import RetrievalResult
from backend.utils import answer_cache
from tests.helpers import make_chunk

GOOD = ChatAnswer(answer="תשובה", source_url="https://www.fnx.co.il/a", found=True, source_title="כותרת")
HISTORY = [ChatMessage(role="user", content="מה זה ביטוח בריאות?"), ChatMessage(role="assistant", content="הסבר")]


@pytest.fixture
def fakes(monkeypatch):
    """Fake the three things chat_service calls. Records what happened in fakes.log."""
    class Fakes:
        log: list[tuple] = []
        rewrite_result = ""
        answer = GOOD

    fake = Fakes()
    fake.log = []

    def generate_text(system_prompt, prompt):
        fake.log.append(("llm_rewrite", prompt))
        return fake.rewrite_result

    def retrieve(question):
        fake.log.append(("retrieve", question))
        return RetrievalResult(chunks=[make_chunk()], best_score=0.9)

    def generate_answer(question, chunks):
        fake.log.append(("generate", question))
        return fake.answer

    def stream_answer(question, chunks):
        fake.log.append(("stream", question))
        yield {"type": "delta", "text": "תש"}
        yield {"type": "final", **fake.answer.model_dump()}

    monkeypatch.setattr(chat, "generate_text", generate_text)
    monkeypatch.setattr(chat, "retrieve", retrieve)
    monkeypatch.setattr(chat, "generate_answer", generate_answer)
    monkeypatch.setattr(chat, "stream_answer", stream_answer)
    return fake


def steps(fake):
    return [entry[0] for entry in fake.log]


# --- thank-you shortcut ---

@pytest.mark.parametrize("message", ["תודה", "תודה רבה", "תודה רבה לך!", "thanks", "Thanks a lot", "thank you so much", "תודה על העזרה"])
def test_a_thank_you_gets_a_reply(message):
    assert chat._thanks_reply(message) is not None


@pytest.mark.parametrize("message", [
    "תודה, ומה לגבי ניתוח?",      # a question mark
    "תודה אבל מה הכיסוי בניתוח",  # more than a thank-you
    "מה הכיסוי בביטוח בריאות",    # no thanks word
    "תודה רבה לך על כל העזרה שלך היום",  # too long
    "",
    "   ",
])
def test_other_messages_are_not_a_thank_you(message):
    assert chat._thanks_reply(message) is None


def test_the_thank_you_language_follows_the_message():
    assert chat._thanks_reply("תודה רבה") in chat.THANKS_REPLIES_HE
    assert chat._thanks_reply("thanks") in chat.THANKS_REPLIES_EN


def test_a_thank_you_makes_no_search_and_no_llm_call(fakes):
    answer = chat.answer_question("תודה רבה", HISTORY)
    assert answer.found is True and answer.source_url is None
    assert fakes.log == []


def test_a_thank_you_in_streaming_is_one_final_event(fakes):
    events = list(chat.stream_answer_question("thanks", HISTORY))
    assert [e["type"] for e in events] == ["final"] and events[0]["found"] is True
    assert fakes.log == []


# --- rewrite ---

def test_the_first_question_is_not_rewritten(fakes):
    assert chat.rewrite_question("מה הכיסוי?", []) == "מה הכיסוי?"
    assert fakes.log == []


def test_a_follow_up_is_rewritten_with_the_history(fakes):
    fakes.rewrite_result = "מה הכיסוי בביטוח בריאות?"
    assert chat.rewrite_question("ומה הכיסוי?", HISTORY) == "מה הכיסוי בביטוח בריאות?"
    prompt = fakes.log[0][1]
    assert "מה זה ביטוח בריאות?" in prompt and "ומה הכיסוי?" in prompt


def test_an_empty_rewrite_keeps_the_original_question(fakes):
    fakes.rewrite_result = ""
    assert chat.rewrite_question("ומה הכיסוי?", HISTORY) == "ומה הכיסוי?"


def test_only_the_last_messages_are_sent_to_the_rewrite(fakes):
    long_history = [ChatMessage(role="user", content=f"message {i}") for i in range(20)]
    fakes.rewrite_result = "x"
    chat.answer_question("follow-up", long_history)
    prompt = fakes.log[0][1]
    assert "message 19" in prompt and "message 14" in prompt
    assert "message 13" not in prompt  # MAX_HISTORY_MESSAGES = 6


# --- the normal flow ---

def test_a_new_question_is_searched_then_answered_with_the_rewritten_text(fakes):
    fakes.rewrite_result = "שאלה מלאה"
    answer = chat.answer_question("ומה זה?", HISTORY)
    assert answer == GOOD
    assert fakes.log[1:] == [("retrieve", "שאלה מלאה"), ("generate", "שאלה מלאה")]


def test_a_found_answer_is_cached_and_reused(fakes):
    chat.answer_question("מה הכיסוי?")
    fakes.log.clear()
    assert chat.answer_question("מה הכיסוי?") == GOOD
    assert fakes.log == []  # no search, no LLM


def test_the_cache_ignores_case_and_punctuation(fakes):
    chat.answer_question("How do I file a claim?")
    fakes.log.clear()
    chat.answer_question("how do i file a claim")
    assert fakes.log == []


def test_a_not_found_answer_is_not_cached(fakes):
    fakes.answer = ChatAnswer(answer="לא באתר", source_url=None, found=False)
    chat.answer_question("שאלה מוזרה")
    chat.answer_question("שאלה מוזרה")
    assert steps(fakes).count("generate") == 2


# --- streaming ---

def test_streaming_passes_the_events_through_and_caches_the_final(fakes):
    events = list(chat.stream_answer_question("מה הכיסוי?"))
    assert [e["type"] for e in events] == ["delta", "final"]
    assert answer_cache.get("מה הכיסוי?") == GOOD.model_dump()  # the "type" key is not stored


def test_streaming_a_cached_answer_sends_the_text_then_the_final(fakes):
    chat.answer_question("מה הכיסוי?")
    fakes.log.clear()
    events = list(chat.stream_answer_question("מה הכיסוי?"))
    assert events[0] == {"type": "delta", "text": "תשובה"}
    assert events[1]["type"] == "final" and events[1]["answer"] == "תשובה"
    assert fakes.log == []
