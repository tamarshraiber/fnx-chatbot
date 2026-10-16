from dataclasses import dataclass, field

from backend.config import RELEVANCE_THRESHOLD, TOP_K
from backend.repositories import vector_repository
from backend.services.embedding_service import embed_question


@dataclass
class RetrievalResult:
    # Chunks at or above the cutoff, best first. Each has url, title, text, similarity.
    chunks: list[dict] = field(default_factory=list)
    # Best similarity found, even if it is below the cutoff (useful for tuning).
    best_score: float = 0.0

    @property
    def found(self) -> bool:
        """True if at least one chunk is relevant enough to answer from."""
        return bool(self.chunks)


def retrieve(question: str, top_k: int = TOP_K, threshold: float = RELEVANCE_THRESHOLD) -> RetrievalResult:
    """Find the chunks closest to the question and drop the ones below the cutoff."""
    matches = vector_repository.search(embed_question(question), top_k=top_k)
    if not matches:
        return RetrievalResult()

    best_score = max(match["similarity"] for match in matches)
    relevant = [match for match in matches if match["similarity"] >= threshold]
    relevant.sort(key=lambda match: match["similarity"], reverse=True)
    return RetrievalResult(chunks=relevant, best_score=best_score)
