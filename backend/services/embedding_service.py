import os

# The default Hugging Face download protocol ("xet") is blocked by some filters (NetFree) and fails
# on the big model file. The normal protocol works. This must be set before the import below.
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

from sentence_transformers import SentenceTransformer  # noqa: E402

from backend.config import EMBEDDING_DIMENSIONS, EMBEDDING_MODEL

# How many texts the model processes at once (a bigger batch uses more memory).
BATCH_SIZE = 16

# E5 models were trained with these prefixes: "passage: " for documents, "query: " for questions.
# Without them the search quality drops.
DOCUMENT_PREFIX = "passage: "
QUERY_PREFIX = "query: "

_model: SentenceTransformer | None = None


def _get_model() -> SentenceTransformer:
    """Load the model once and reuse it (the first load downloads it and takes a while)."""
    global _model
    if _model is None:
        _model = SentenceTransformer(EMBEDDING_MODEL)
        size = _model.get_embedding_dimension()
        if size != EMBEDDING_DIMENSIONS:
            raise RuntimeError(
                f"Model {EMBEDDING_MODEL} makes vectors of size {size}, but the database expects {EMBEDDING_DIMENSIONS}."
            )
    return _model


def _embed(texts: list[str], prefix: str) -> list[list[float]]:
    # normalize_embeddings=True scales each vector to length 1, so the dot product is the cosine similarity.
    vectors = _get_model().encode(
        [prefix + text for text in texts],
        batch_size=BATCH_SIZE,
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    return vectors.tolist()


def embed_chunks(texts: list[str]) -> list[list[float]]:
    """Embed many chunk texts (used when we build the database)."""
    return _embed(texts, DOCUMENT_PREFIX)


def embed_question(question: str) -> list[float]:
    """Embed one user question (used at question time)."""
    return _embed([question], QUERY_PREFIX)[0]
