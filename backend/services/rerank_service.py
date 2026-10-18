import cohere

from backend.config import COHERE_API_KEY, RERANK_MODEL

_client: cohere.ClientV2 | None = None


def _get_client() -> cohere.ClientV2:
    """Create the Cohere client once and reuse it."""
    global _client
    if _client is None:
        if not COHERE_API_KEY:
            raise RuntimeError("COHERE_API_KEY is missing. Add it to your .env file.")
        _client = cohere.ClientV2(api_key=COHERE_API_KEY)
    return _client


def rerank(question: str, chunks: list[dict], top_n: int) -> list[dict]:
    """Re-score the chunks against the question. Returns the best top_n, best first.

    Each returned chunk is a copy of the original with an extra 'rerank_score' (0 to 1, higher = better).
    """
    if not chunks:
        return []
    response = _get_client().rerank(
        model=RERANK_MODEL,
        query=question,
        documents=[chunk["text"] for chunk in chunks],
        top_n=min(top_n, len(chunks)),
    )
    return [
        {**chunks[result.index], "rerank_score": result.relevance_score}
        for result in response.results
    ]
