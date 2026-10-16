import math
import time

from google import genai
from google.genai import types

from backend.config import EMBEDDING_DIMENSIONS, EMBEDDING_MODEL, require_gemini_key
from backend.utils.retry import call_with_retry

# How many texts we send in one request, and the pause between requests (free-tier limits).
BATCH_SIZE = 20
PAUSE_SECONDS = 1.0


_client: genai.Client | None = None


def _get_client() -> genai.Client:
    """Create the Gemini client once and reuse it."""
    global _client
    if _client is None:
        _client = genai.Client(api_key=require_gemini_key())
    return _client


def _normalize(vector: list[float]) -> list[float]:
    """Scale the vector to length 1. Gemini asks for this when the size is below 3072."""
    length = math.sqrt(sum(value * value for value in vector))
    return [value / length for value in vector] if length else vector


def _embed(texts: list[str], task_type: str) -> list[list[float]]:
    response = _get_client().models.embed_content(
        model=EMBEDDING_MODEL,
        contents=texts,
        config=types.EmbedContentConfig(
            task_type=task_type,
            output_dimensionality=EMBEDDING_DIMENSIONS,
        ),
    )
    return [_normalize(list(item.values)) for item in response.embeddings]


def embed_chunks(texts: list[str]) -> list[list[float]]:
    """Embed many chunk texts (used when we build the database)."""
    vectors: list[list[float]] = []
    for start in range(0, len(texts), BATCH_SIZE):
        if start:
            time.sleep(PAUSE_SECONDS)
        vectors.extend(_embed(texts[start:start + BATCH_SIZE], "RETRIEVAL_DOCUMENT"))
    return vectors


def embed_question(question: str) -> list[float]:
    """Embed one user question (used at question time). Retries on temporary Gemini errors."""
    return call_with_retry(lambda: _embed([question], "RETRIEVAL_QUERY"))[0]
