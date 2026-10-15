from supabase import Client, create_client

from backend.config import require_supabase_settings

TABLE = "chunks"
# How many rows we send to Supabase in one request.
UPSERT_BATCH_SIZE = 50

_client: Client | None = None


def _get_client() -> Client:
    """Create the Supabase client once and reuse it."""
    global _client
    if _client is None:
        url, key = require_supabase_settings()
        _client = create_client(url, key)
    return _client


def upsert_chunks(rows: list[dict]) -> int:
    """Insert new chunks or overwrite existing ones (same chunk_id). Returns the row count.

    Each row needs: chunk_id, url, title, text, chunk_index, embedding.
    It may also have: lastmod, content_hash, crawled_at.
    """
    client = _get_client()
    for start in range(0, len(rows), UPSERT_BATCH_SIZE):
        batch = rows[start:start + UPSERT_BATCH_SIZE]
        client.table(TABLE).upsert(batch, on_conflict="chunk_id").execute()
    return len(rows)


def search(query_embedding: list[float], top_k: int = 5) -> list[dict]:
    """Return the top_k closest chunks, each with a 'similarity' score (higher = closer)."""
    response = _get_client().rpc(
        "match_chunks",
        {"query_embedding": query_embedding, "match_count": top_k},
    ).execute()
    return response.data


def delete_by_url(url: str) -> None:
    """Delete all chunks of one page (used when a page is removed or changed)."""
    _get_client().table(TABLE).delete().eq("url", url).execute()
