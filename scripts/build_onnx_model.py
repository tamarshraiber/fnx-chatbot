"""Build the compact copy of the embedding model used by the light mode (EMBEDDING_ONNX_DIR).

Why: the full model needs over 1 GB of memory, but a free server has only 512 MB. The memory goes to the word table
(250,000 words) and the tokenizer, not to the 12 layers. So we split the model into parts:
  word_emb.npy            the word table, read from disk row by row (only the words of the question are loaded)
  sentencepiece.bpe.model the small tokenizer (the fast tokenizer needs 260 MB, this one about 45 MB)
  layers_int8.onnx        the 12 layers, shrunk to int8 (about 80 MB instead of 330 MB)
The vectors differ from the full model by about 0.01, so the stored document vectors stay valid.

The script ends by comparing the compact copy with the full model, and fails if they differ too much.

Run:  python -m scripts.build_onnx_model <output folder>
Needs: torch, sentence-transformers, onnx, onnxruntime, sentencepiece (only for building, not on the server).
"""
import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("HF_HUB_DISABLE_XET", "1")

import numpy as np  # noqa: E402
import torch  # noqa: E402
from huggingface_hub import hf_hub_download  # noqa: E402
from onnxruntime.quantization import QuantType, quantize_dynamic  # noqa: E402
from sentence_transformers import SentenceTransformer  # noqa: E402

from backend.config import EMBEDDING_DIMENSIONS, EMBEDDING_MODEL  # noqa: E402
from backend.services import embedding_service  # noqa: E402

# The compact copy must be at least this similar (cosine) to the full model on every check text.
# It was 0.98 or higher when we tested it on real questions.
MIN_COSINE = 0.97
CHECK_TEXTS = [
    "איך אפשר ליצור קשר עם שירות הלקוחות?",
    "מה מספר הטלפון של שירות הלקוחות?",
    "איך מגישים תביעה בביטוח רכב?",
    "מה כולל ביטוח בריאות?",
    "What is the capital of France?",
]


class _Layers(torch.nn.Module):
    """The 12 layers only: they take the word vectors as input, so the word table can stay outside the graph."""

    def __init__(self, model):
        super().__init__()
        self.model = model

    def forward(self, inputs_embeds, attention_mask):
        return self.model(inputs_embeds=inputs_embeds, attention_mask=attention_mask).last_hidden_state


def build(out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    full = SentenceTransformer(EMBEDDING_MODEL)
    full.eval()
    layers = full[0].auto_model

    print("1/4 saving the word table")
    table = layers.embeddings.word_embeddings.weight.detach().numpy().astype(np.float32)
    np.save(out_dir / "word_emb.npy", table)

    print("2/4 copying the tokenizer file")
    hf_hub_download(EMBEDDING_MODEL, "sentencepiece.bpe.model", local_dir=out_dir)

    print("3/4 exporting the layers and shrinking them to int8")
    inputs = full.tokenizer(["query: שלום עולם"], return_tensors="pt")
    word_vectors = layers.embeddings.word_embeddings(inputs["input_ids"])
    with tempfile.TemporaryDirectory() as tmp:
        full_graph = os.path.join(tmp, "layers.onnx")
        torch.onnx.export(
            _Layers(layers),
            (word_vectors, inputs["attention_mask"]),
            full_graph,
            input_names=["inputs_embeds", "attention_mask"],
            output_names=["last_hidden_state"],
            dynamic_axes={
                "inputs_embeds": {0: "batch", 1: "length"},
                "attention_mask": {0: "batch", 1: "length"},
                "last_hidden_state": {0: "batch", 1: "length"},
            },
            opset_version=17,
            dynamo=False,
        )
        quantize_dynamic(full_graph, str(out_dir / "layers_int8.onnx"), weight_type=QuantType.QInt8, per_channel=True)

    print("4/4 checking the compact copy against the full model")
    compact = embedding_service.load_onnx_model(str(out_dir))
    worst = 1.0
    for text in CHECK_TEXTS:
        exact = full.encode(["query: " + text], normalize_embeddings=True)[0]
        light = np.array(embedding_service.embed_with_onnx(compact, text))
        if len(light) != EMBEDDING_DIMENSIONS:
            raise SystemExit(f"FAILED: vector size {len(light)}, expected {EMBEDDING_DIMENSIONS}")
        worst = min(worst, float(exact @ light))
    print(f"lowest cosine to the full model: {worst:.4f} (must be at least {MIN_COSINE})")
    if worst < MIN_COSINE:
        raise SystemExit("FAILED: the compact copy is too different from the full model")
    print(f"OK. Files are in {out_dir}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python -m scripts.build_onnx_model <output folder>")
    build(Path(sys.argv[1]))
