from dataclasses import dataclass, field

from backend.config import (
    RELEVANCE_THRESHOLD,
    RERANK_ENABLED,
    RERANK_FETCH_K,
    RERANK_THRESHOLD,
    TOP_K,
)
from backend.repositories import vector_repository
from backend.services import rerank_service
from backend.services.embedding_service import embed_question


@dataclass
class RetrievalResult:
    # Chunks at or above the cutoff, best first. Each has url, title, text, similarity.
    # When reranking is used, each also has rerank_score.
    chunks: list[dict] = field(default_factory=list)
    # Best score found, even if it is below the cutoff (useful for tuning).
    # It is the rerank score when reranking was used, otherwise the vector similarity.
    best_score: float = 0.0

    @property
    def found(self) -> bool:
        """True if at least one chunk is relevant enough to answer from."""
        return bool(self.chunks)


def retrieve(
    question: str,
    top_k: int = TOP_K,
    threshold: float | None = None,
    use_rerank: bool | None = None,
) -> RetrievalResult:
    """Find the chunks closest to the question and drop the ones below the cutoff.

    With reranking: fetch more chunks, let Cohere re-score them, keep the best top_k.
    If Cohere fails (for example the trial limit), we fall back to plain vector search.
    """
    if use_rerank is None:
        use_rerank = RERANK_ENABLED

    if use_rerank:
        try:
            return _retrieve_reranked(question, top_k, RERANK_THRESHOLD if threshold is None else threshold)
        except Exception as error:  # keep the chatbot working if Cohere is down or over its limit
            print(f"Rerank failed ({type(error).__name__}). Using plain vector search.")

    return _retrieve_vector(question, top_k, RELEVANCE_THRESHOLD if threshold is None else threshold)


def _retrieve_vector(question: str, top_k: int, threshold: float) -> RetrievalResult:
    matches = vector_repository.search(embed_question(question), top_k=top_k)
    if not matches:
        return RetrievalResult()

    best_score = max(match["similarity"] for match in matches)
    relevant = [match for match in matches if match["similarity"] >= threshold]
    relevant.sort(key=lambda match: match["similarity"], reverse=True)
    return RetrievalResult(chunks=relevant, best_score=best_score)


def _retrieve_reranked(question: str, top_k: int, threshold: float) -> RetrievalResult:
    candidates = vector_repository.search(embed_question(question), top_k=RERANK_FETCH_K)
    reranked = rerank_service.rerank(question, candidates, top_n=top_k)
    if not reranked:
        return RetrievalResult()

    best_score = max(chunk["rerank_score"] for chunk in reranked)
    relevant = [chunk for chunk in reranked if chunk["rerank_score"] >= threshold]
    return RetrievalResult(chunks=relevant, best_score=best_score)
