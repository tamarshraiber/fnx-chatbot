"""Insert one test row, search for it, delete it. Proves the Supabase table and search work."""
from backend.config import EMBEDDING_DIMENSIONS
from backend.repositories import vector_repository
from backend.services.embedding_service import embed_chunks, embed_question

TEST_URL = "https://example.com/check-supabase"
TEST_TEXT = "בדיקת חיבור: שמאי רכב בוחן את הנזק שנגרם לרכב לאחר תאונה."


def main() -> None:
    vector = embed_chunks([TEST_TEXT])[0]
    row = {
        "chunk_id": "check-supabase-0",
        "chunk_index": 0,
        "url": TEST_URL,
        "title": "Test page",
        "text": TEST_TEXT,
        "embedding": vector,
    }

    try:
        count = vector_repository.upsert_chunks([row])
        print(f"Saved {count} test row (vector size {EMBEDDING_DIMENSIONS})")

        # Saving the same row again must not create a duplicate.
        vector_repository.upsert_chunks([row])

        results = vector_repository.search(embed_question("מה עושה שמאי רכב?"), top_k=3)
        found = [r for r in results if r["url"] == TEST_URL]
        print(f"Search returned {len(results)} row(s)")
        if found:
            print(f"Test row found, similarity {found[0]['similarity']:.3f}")
        else:
            print("PROBLEM: test row was not found by the search")
    finally:
        vector_repository.delete_by_url(TEST_URL)
        print("Test row deleted")


if __name__ == "__main__":
    main()
