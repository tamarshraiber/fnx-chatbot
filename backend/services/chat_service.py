from backend.models.schemas import ChatAnswer, ChatMessage
from backend.services.generation_service import generate_answer
from backend.services.llm_service import generate_text
from backend.services.retrieval_service import retrieve

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
    recent = (history or [])[-MAX_HISTORY_MESSAGES:]
    standalone = rewrite_question(question, recent)
    result = retrieve(standalone)
    return generate_answer(standalone, result.chunks)
