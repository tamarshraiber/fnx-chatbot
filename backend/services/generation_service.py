import re
from typing import Iterator

from backend.models.schemas import ChatAnswer, LLMAnswer
from backend.services.llm_service import generate_json, stream_text

NOT_ON_WEBSITE = "מידע זה אינו מופיע באתר. מומלץ לפנות לשירות הלקוחות של הפניקס."

SYSTEM_PROMPT = """You are a customer-information assistant for Phoenix Insurance (fnx.co.il).
Answer the user's question in Hebrew, using ONLY the text in the provided chunks.

Rules:
- Never use outside knowledge and never guess. If the chunks do not clearly contain the answer, set answerable=false.
- Keep the answer short, clear and in simple Hebrew.
- Write correct Hebrew spacing: always put a space between words, including before a word that starts with the letter ו (for example "ניתוח ולאשפוז", "ולאחר מכן", "אזרח ותיק").
- source_url must be copied exactly from the URL of the chunk you used. Never invent a URL.
- If the user asks about their own personal policy, coverage, price or claim status, explain in general terms what the chunks say, and tell them to contact customer service for their personal details.
- If the user asks for medical, legal or financial advice, do not give advice. Explain only what the chunks say and suggest a professional or customer service.
"""

# Streaming version of the prompt: plain text instead of JSON, so the words can be shown while they are written.
STREAM_SYSTEM_PROMPT = """You are a customer-information assistant for Phoenix Insurance (fnx.co.il).
Answer the user's question in Hebrew, using ONLY the text in the provided chunks.

Rules:
- Never use outside knowledge and never guess. If the chunks do not clearly contain the answer, reply with exactly the single word NOT_FOUND and nothing else.
- Keep the answer short, clear and in simple Hebrew. Write plain text only, with no markdown.
- Write correct Hebrew spacing: always put a space between words, including before a word that starts with the letter ו (for example "ניתוח ולאשפוז", "ולאחר מכן", "אזרח ותיק").
- When you do answer, write the answer first. Then, on a new last line, write SOURCE: followed by the URL of the chunk you used, copied exactly. Never invent a URL.
- If the user asks about their own personal policy, coverage, price or claim status, explain in general terms what the chunks say, and tell them to contact customer service for their personal details.
- If the user asks for medical, legal or financial advice, do not give advice. Explain only what the chunks say and suggest a professional or customer service.
"""

NOT_FOUND_MARKER = "NOT_FOUND"
SOURCE_MARKER = "SOURCE:"


def _build_prompt(question: str, chunks: list[dict]) -> str:
    parts = [f"URL: {chunk['url']}\nTitle: {chunk['title']}\nText:\n{chunk['text']}" for chunk in chunks]
    return "Chunks:\n\n" + "\n\n---\n\n".join(parts) + f"\n\nQuestion: {question}"


# A site suffix at the end of a page title, such as " | הפניקס" or " - Phoenix".
_SITE_SUFFIX = re.compile(r"\s*[|\-–—:]\s*[^|\-–—:]*(הפניקס|phoenix|fnx)[^|\-–—:]*$", re.IGNORECASE)


def _clean_title(title: str) -> str | None:
    """Remove the site name from the end of a page title. Returns None if nothing is left."""
    cleaned = _SITE_SUFFIX.sub("", title or "").strip()
    return cleaned or None


def _not_on_website() -> ChatAnswer:
    return ChatAnswer(answer=NOT_ON_WEBSITE, source_url=None, found=False)


def generate_answer(question: str, chunks: list[dict]) -> ChatAnswer:
    """Answer from the chunks only. Falls back to the fixed reply when unsure."""
    if not chunks:
        return _not_on_website()  # nothing relevant, so we do not even call the LLM

    # Tries Gemini, then Groq, then OpenRouter (see llm_service.py).
    result = generate_json(SYSTEM_PROMPT, _build_prompt(question, chunks), LLMAnswer)
    if not result.answerable or not result.answer.strip():
        return _not_on_website()

    # The cited URL must be one we actually retrieved.
    titles_by_url = {chunk["url"]: chunk.get("title", "") for chunk in chunks}
    if result.source_url not in titles_by_url:
        return _not_on_website()

    return ChatAnswer(
        answer=result.answer.strip(),
        source_url=result.source_url,
        found=True,
        source_title=_clean_title(titles_by_url[result.source_url]),
    )


def _finish_stream(text: str, chunks: list[dict]) -> ChatAnswer:
    """Build the final answer from the whole streamed text: split off the SOURCE line and check the URL."""
    index = text.rfind(SOURCE_MARKER)
    answer = (text if index < 0 else text[:index]).strip()
    if not answer:
        return _not_on_website()

    titles_by_url = {chunk["url"]: chunk.get("title", "") for chunk in chunks}
    url = text[index + len(SOURCE_MARKER):].strip().strip("<>()[]\"'`*").rstrip(".,") if index >= 0 else ""
    # The words are already on screen, so a missing or wrong URL only means: no source card.
    if url not in titles_by_url:
        return ChatAnswer(answer=answer, source_url=None, found=True)
    return ChatAnswer(answer=answer, source_url=url, found=True, source_title=_clean_title(titles_by_url[url]))


def stream_answer(question: str, chunks: list[dict]) -> Iterator[dict]:
    """Answer from the chunks only, as events: {"type": "delta", "text": ...} then one {"type": "final", ...}."""
    if not chunks:
        yield {"type": "final", **_not_on_website().model_dump()}
        return

    text = ""      # everything the model wrote so far
    sent = 0       # how many characters of `text` the user has already received
    deciding = True  # until we know the reply is not NOT_FOUND, nothing is sent
    # Hold back the end of the text, because it may be the start of the SOURCE line.
    hold = len(SOURCE_MARKER) - 1

    for piece in stream_text(STREAM_SYSTEM_PROMPT, _build_prompt(question, chunks)):
        text += piece
        if deciding:
            start = text.lstrip()
            if NOT_FOUND_MARKER.startswith(start) and len(start) < len(NOT_FOUND_MARKER):
                continue  # too short to tell yet
            if start.startswith(NOT_FOUND_MARKER):
                yield {"type": "final", **_not_on_website().model_dump()}
                return
            deciding = False
            text = start
        marker = text.find(SOURCE_MARKER)
        safe_end = marker if marker >= 0 else len(text) - hold
        if safe_end > sent:
            yield {"type": "delta", "text": text[sent:safe_end]}
            sent = safe_end

    if deciding and text.strip().startswith(NOT_FOUND_MARKER) or not text.strip():
        yield {"type": "final", **_not_on_website().model_dump()}
        return
    yield {"type": "final", **_finish_stream(text.lstrip(), chunks).model_dump()}
