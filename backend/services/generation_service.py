from backend.models.schemas import ChatAnswer, LLMAnswer
from backend.services.llm_service import generate_json

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

def _build_prompt(question: str, chunks: list[dict]) -> str:
    parts = [f"URL: {chunk['url']}\nTitle: {chunk['title']}\nText:\n{chunk['text']}" for chunk in chunks]
    return "Chunks:\n\n" + "\n\n---\n\n".join(parts) + f"\n\nQuestion: {question}"


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
    retrieved_urls = {chunk["url"] for chunk in chunks}
    if result.source_url not in retrieved_urls:
        return _not_on_website()

    return ChatAnswer(answer=result.answer.strip(), source_url=result.source_url, found=True)
