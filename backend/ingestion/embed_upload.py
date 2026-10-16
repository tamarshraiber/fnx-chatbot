"""Embed all chunks and upload them to Supabase. Safe to run again (no duplicates).

Run:  python -m backend.ingestion.embed_upload
"""
import json
from pathlib import Path

from backend.repositories import vector_repository
from backend.services.embedding_service import embed_chunks

CHUNKS_FILE = Path(__file__).resolve().parents[2] / "data" / "chunks" / "chunks.json"


def load_chunks() -> list[dict]:
    with open(CHUNKS_FILE, encoding="utf-8") as f:
        return json.load(f)


def main() -> None:
    chunks = load_chunks()
    print(f"Read {len(chunks)} chunks from {CHUNKS_FILE}")

    vectors = embed_chunks([chunk["text"] for chunk in chunks])
    print(f"Created {len(vectors)} embeddings")

    rows = [
        {
            "chunk_id": chunk["chunk_id"],
            "url": chunk["url"],
            "title": chunk.get("title", ""),
            "text": chunk["text"],
            "chunk_index": chunk["chunk_index"],
            "lastmod": chunk.get("lastmod"),
            "embedding": vector,
        }
        for chunk, vector in zip(chunks, vectors)
    ]

    # Delete the old rows of each page first, so chunks that no longer exist do not stay behind.
    urls = sorted({row["url"] for row in rows})
    for url in urls:
        vector_repository.delete_by_url(url)

    count = vector_repository.upsert_chunks(rows)
    print(f"Uploaded {count} rows for {len(urls)} pages")


if __name__ == "__main__":
    main()
