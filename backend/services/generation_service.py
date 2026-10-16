from google import genai
from google.genai import types

from backend.config import GEMINI_MODEL, require_gemini_key
from backend.models.schemas import ChatAnswer, LLMAnswer
from backend.utils.retry import call_with_retry

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

_client: genai.Client | None = None


def _get_client() -> genai.Client:
    """Create the Gemini client once and reuse it."""
    global _client
    if _client is None:
        _client = genai.Client(api_key=require_gemini_key())
    return _client


def _build_prompt(question: str, chunks: list[dict]) -> str:
    parts = [f"URL: {chunk['url']}\nTitle: {chunk['title']}\nText:\n{chunk['text']}" for chunk in chunks]
    return "Chunks:\n\n" + "\n\n---\n\n".join(parts) + f"\n\nQuestion: {question}"


def _not_on_website() -> ChatAnswer:
    return ChatAnswer(answer=NOT_ON_WEBSITE, source_url=None, found=False)


def generate_answer(question: str, chunks: list[dict]) -> ChatAnswer:
    """Answer from the chunks only. Falls back to the fixed reply when unsure."""
    if not chunks:
        return _not_on_website()  # nothing relevant, so we do not even call the LLM

    response = call_with_retry(lambda: _get_client().models.generate_content(
        model=GEMINI_MODEL,
        contents=_build_prompt(question, chunks),
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            response_mime_type="application/json",
            response_schema=LLMAnswer,
            temperature=0.0,
        ),
    ))
    result = response.parsed
    if result is None or not result.answerable or not result.answer.strip():
        return _not_on_website()

    # The cited URL must be one we actually retrieved.
    retrieved_urls = {chunk["url"] for chunk in chunks}
    if result.source_url not in retrieved_urls:
        return _not_on_website()

    return ChatAnswer(answer=result.answer.strip(), source_url=result.source_url, found=True)
