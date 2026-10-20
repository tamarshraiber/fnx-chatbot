import os

# The default Hugging Face download protocol ("xet") is blocked by some filters (NetFree) and fails
# on the big model file. The normal protocol works. This must be set before the model is loaded.
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

from backend.config import EMBEDDING_DIMENSIONS, EMBEDDING_MODEL, EMBEDDING_ONNX_DIR

# How many texts the model processes at once (a bigger batch uses more memory).
BATCH_SIZE = 16

# E5 models were trained with these prefixes: "passage: " for documents, "query: " for questions.
# Without them the search quality drops.
DOCUMENT_PREFIX = "passage: "
QUERY_PREFIX = "query: "

# The model reads at most this many tokens.
MAX_TOKENS = 512

_model = None  # the full model (sentence-transformers), loaded on first use
_onnx_model = None  # the compact model (light mode), loaded on first use


def _get_model():
    """Load the full model once and reuse it (the first load downloads it and takes a while)."""
    global _model
    if _model is None:
        # Imported here, so a server that only uses the compact model does not need torch at all.
        from sentence_transformers import SentenceTransformer

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


def load_onnx_model(folder: str) -> dict:
    """Load the compact model made by scripts/build_onnx_model.py (see that file for why it is split in parts)."""
    import numpy as np
    import onnxruntime
    import sentencepiece

    options = onnxruntime.SessionOptions()
    options.intra_op_num_threads = 1  # the server has very little CPU, more threads would not help
    return {
        "tokenizer": sentencepiece.SentencePieceProcessor(model_file=os.path.join(folder, "sentencepiece.bpe.model")),
        # mmap_mode="r": the table stays on disk and only the rows of the words in the question are read.
        "word_table": np.load(os.path.join(folder, "word_emb.npy"), mmap_mode="r"),
        "session": onnxruntime.InferenceSession(
            os.path.join(folder, "layers_int8.onnx"), options, providers=["CPUExecutionProvider"]
        ),
    }


def embed_with_onnx(onnx_model: dict, text: str) -> list[float]:
    """Embed one question with the compact model. Gives the same kind of vector as _embed (length 1)."""
    import numpy as np

    # Same ids as the standard XLM-R tokenizer: <s>=0, <pad>=1, </s>=2, <unk>=3, other pieces = sentencepiece id + 1.
    pieces = onnx_model["tokenizer"].encode(QUERY_PREFIX + text)[: MAX_TOKENS - 2]
    ids = np.array([0] + [3 if piece == 0 else piece + 1 for piece in pieces] + [2])
    output = onnx_model["session"].run(
        None,
        {
            "inputs_embeds": np.asarray(onnx_model["word_table"][ids], dtype=np.float32)[None],
            "attention_mask": np.ones((1, len(ids)), dtype=np.int64),
        },
    )[0]
    vector = output.mean(axis=1)[0]  # one question, no padding: mean pooling is the plain average
    return (vector / np.linalg.norm(vector)).tolist()


def embed_chunks(texts: list[str]) -> list[list[float]]:
    """Embed many chunk texts (used when we build the database). Always the full model."""
    return _embed(texts, DOCUMENT_PREFIX)


def embed_question(question: str) -> list[float]:
    """Embed one user question (used at question time)."""
    global _onnx_model
    if EMBEDDING_ONNX_DIR:
        if _onnx_model is None:
            _onnx_model = load_onnx_model(EMBEDDING_ONNX_DIR)
        return embed_with_onnx(_onnx_model, question)
    return _embed([question], QUERY_PREFIX)[0]
