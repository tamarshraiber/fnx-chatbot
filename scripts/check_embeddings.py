"""Embed a few chunks and one question, and show which chunk is closest to the question."""
import json

from backend.config import EMBEDDING_DIMENSIONS, EMBEDDING_MODEL
from backend.ingestion import config
from backend.services.embedding_service import embed_chunks, embed_question

QUESTION = "איך בוחרים שמאי רכב?"


def similarity(a: list[float], b: list[float]) -> float:
    """Vectors have length 1, so the dot product is the cosine similarity."""
    return sum(x * y for x, y in zip(a, b))


def main() -> None:
    chunks = json.loads((config.CHUNKS_DIR / "chunks.json").read_text(encoding="utf-8"))
    # One chunk from each page (the first chunk of each), so the topics are different.
    samples = [chunk for chunk in chunks if chunk["chunk_index"] == 0]

    vectors = embed_chunks([chunk["text"] for chunk in samples])
    question_vector = embed_question(QUESTION)

    print(f"Model: {EMBEDDING_MODEL}")
    print(f"Vector size: {len(question_vector)} (expected {EMBEDDING_DIMENSIONS})")
    print(f"Question: {QUESTION}\n")

    scored = sorted(
        ((similarity(question_vector, vector), chunk) for vector, chunk in zip(vectors, samples)),
        key=lambda pair: pair[0],
        reverse=True,
    )
    for score, chunk in scored:
        print(f"{score:.3f}  {chunk['title']}")


if __name__ == "__main__":
    main()
