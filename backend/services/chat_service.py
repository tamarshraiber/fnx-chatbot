import random
import re
import time
from typing import Iterator

from backend.models.schemas import ChatAnswer, ChatMessage
from backend.services.generation_service import generate_answer, stream_answer
from backend.services.llm_service import generate_text
from backend.services.retrieval_service import retrieve

# A message that is only a thank-you gets a friendly reply at once, with no search and no LLM call.
THANKS_WORDS = {"תודה", "תודות", "תנקס", "thanks", "thank", "thx", "ty"}
THANKS_FILLER = {
    "רבה", "רבות", "מאוד", "מאד", "לך", "לכם", "על", "העזרה", "עזרה", "הכל", "הכול", "המידע", "ענקית", "גדולה",
    "מעולה", "אחלה", "מושלם", "יופי", "you", "so", "very", "much", "a", "lot", "for", "the", "help", "all",
}
THANKS_REPLIES_HE = [
    "בשמחה! 😊 אם יש עוד שאלה, אני כאן.",
    "תמיד כאן בשבילך! 🧡",
    "שמחתי לעזור! אפשר לשאול אותי עוד על ביטוחי הפניקס.",
    "בכיף! יום נפלא 🌟",
]
THANKS_REPLIES_EN = [
    "Happy to help! 😊",
    "Always at your service! 🧡",
    "Anytime! Ask me anything else about Phoenix insurance.",
]


def _thanks_reply(question: str) -> str | None:
    """A cute reply if the whole message is a thank-you, otherwise None."""
    if "?" in question or "؟" in question:
        return None
    words = re.findall(r"[\w']+", question.lower())
    if not words or len(words) > 5:
        return None
    if not any(word in THANKS_WORDS for word in words):
        return None
    if not all(word in THANKS_WORDS or word in THANKS_FILLER for word in words):
        return None  # something else is in the message, so it goes through the normal flow
    hebrew = re.search(r"[֐-׿]", question) is not None
    return random.choice(THANKS_REPLIES_HE if hebrew else THANKS_REPLIES_EN)

# Only the last messages are used, so the prompt stays small.
MAX_HISTORY_MESSAGES = 6

REWRITE_PROMPT = """Rewrite the user's last question as one complete, standalone question in Hebrew.
Use the conversation to fill in anything the last question leaves out (for example "it", "that surgery").
If the last question is already clear on its own, return it unchanged.
Return only the question, with no explanation and no quotes."""


def _format_history(history: list[ChatMessage]) -> str:
    return "\n".join(f"{message.role}: {message.content}" for message in history)


def rewrite_question(question: str, history: list[ChatMessage]) -> str:
    """Turn a follow-up question into a standalone question, so retrieval can find it."""
    if not history:
        return question  # first question, nothing to fix

    prompt = f"Conversation:\n{_format_history(history)}\n\nLast question: {question}"
    rewritten = generate_text(REWRITE_PROMPT, prompt)
    return rewritten or question  # if the rewrite is empty, keep the original


def answer_question(question: str, history: list[ChatMessage] | None = None) -> ChatAnswer:
    """Answer a question using the recent history. The caller keeps and updates the history."""
    thanks = _thanks_reply(question)
    if thanks:
        return ChatAnswer(answer=thanks, source_url=None, found=True)  # found=True: normal look, no source card

    recent = (history or [])[-MAX_HISTORY_MESSAGES:]
    start = time.perf_counter()
    standalone = rewrite_question(question, recent)
    rewritten = time.perf_counter()
    result = retrieve(standalone)
    retrieved = time.perf_counter()
    answer = generate_answer(standalone, result.chunks)
    done = time.perf_counter()
    print(
        f"timing: rewrite {rewritten - start:.2f}s, retrieve {retrieved - rewritten:.2f}s, "
        f"answer {done - retrieved:.2f}s, total {done - start:.2f}s"
    )
    return answer


def stream_answer_question(question: str, history: list[ChatMessage] | None = None) -> Iterator[dict]:
    """Like answer_question, but yields events as the answer is written (see generation_service.stream_answer)."""
    thanks = _thanks_reply(question)
    if thanks:
        yield {"type": "final", **ChatAnswer(answer=thanks, source_url=None, found=True).model_dump()}
        return

    recent = (history or [])[-MAX_HISTORY_MESSAGES:]
    start = time.perf_counter()
    standalone = rewrite_question(question, recent)
    rewritten = time.perf_counter()
    result = retrieve(standalone)
    retrieved = time.perf_counter()
    print(f"timing: rewrite {rewritten - start:.2f}s, retrieve {retrieved - rewritten:.2f}s (streaming)")
    yield from stream_answer(standalone, result.chunks)
    print(f"timing: total {time.perf_counter() - start:.2f}s (streaming)")
