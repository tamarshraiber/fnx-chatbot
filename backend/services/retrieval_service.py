import logging
from dataclasses import dataclass, field

from backend.config import (
    FETCH_MULTIPLIER,
    NEIGHBOR_CHUNKS,
    NEIGHBOR_PARENTS,
    RELEVANCE_THRESHOLD,
    RERANK_ENABLED,
    RERANK_FETCH_K,
    RERANK_THRESHOLD,
    TOP_K,
)
from backend.repositories import vector_repository
from backend.services import rerank_service
from backend.services.embedding_service import embed_question

logger = logging.getLogger(__name__)


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
            logger.warning(f"Rerank failed ({type(error).__name__}). Using plain vector search.")

    return _retrieve_vector(question, top_k, RELEVANCE_THRESHOLD if threshold is None else threshold)


def _same_text(text: str) -> str:
    """A key for 'identical text': the same page stored under another URL gives the same key."""
    return " ".join(text.split())


def _remove_copies(matches: list[dict]) -> list[dict]:
    """Keep the first chunk of each text. `matches` is best first, so the best copy is kept."""
    seen: set[str] = set()
    unique = []
    for match in matches:
        key = _same_text(match["text"])
        if key not in seen:
            seen.add(key)
            unique.append(match)
    return unique


def _neighbor_ids(chunk_id: str) -> list[str]:
    """Ids of the chunks that follow this one on its page. A chunk id looks like '<page id>-<position>'."""
    page_id, _, position = chunk_id.rpartition("-")
    if not page_id or not position.isdigit():
        return []
    return [f"{page_id}-{int(position) + step}" for step in range(1, NEIGHBOR_CHUNKS + 1)]


def _add_neighbors(chunks: list[dict]) -> list[dict]:
    """Put the chunks that follow the best chunks right after them (the answer is often just below a heading)."""
    wanted = {}  # parent chunk_id -> its neighbor ids
    for chunk in chunks[:NEIGHBOR_PARENTS]:
        wanted[chunk["chunk_id"]] = _neighbor_ids(chunk["chunk_id"])
    all_ids = [neighbor for ids in wanted.values() for neighbor in ids]
    if not all_ids:
        return chunks
    found = {row["chunk_id"]: row for row in vector_repository.get_chunks_by_ids(all_ids)}

    seen = {_same_text(chunk["text"]) for chunk in chunks}
    result = []
    for chunk in chunks:
        result.append(chunk)
        for neighbor_id in wanted.get(chunk["chunk_id"], []):
            row = found.get(neighbor_id)
            if row is None or _same_text(row["text"]) in seen:
                continue  # missing (end of page) or already included
            seen.add(_same_text(row["text"]))
            result.append({**row, "similarity": chunk["similarity"]})  # it comes with its parent's score
    return result


def _retrieve_vector(question: str, top_k: int, threshold: float) -> RetrievalResult:
    matches = vector_repository.search(embed_question(question), top_k=top_k * FETCH_MULTIPLIER)
    if not matches:
        return RetrievalResult()

    best_score = max(match["similarity"] for match in matches)
    relevant = [match for match in _remove_copies(matches) if match["similarity"] >= threshold]
    relevant.sort(key=lambda match: match["similarity"], reverse=True)
    relevant = _add_neighbors(relevant[:top_k])
    return RetrievalResult(chunks=relevant, best_score=best_score)


def _retrieve_reranked(question: str, top_k: int, threshold: float) -> RetrievalResult:
    candidates = vector_repository.search(embed_question(question), top_k=RERANK_FETCH_K)
    reranked = rerank_service.rerank(question, candidates, top_n=top_k)
    if not reranked:
        return RetrievalResult()

    best_score = max(chunk["rerank_score"] for chunk in reranked)
    relevant = [chunk for chunk in reranked if chunk["rerank_score"] >= threshold]
    return RetrievalResult(chunks=relevant, best_score=best_score)
