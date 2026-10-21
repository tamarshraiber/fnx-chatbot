"""Retrieval: cutoff, duplicate removal, neighbor chunks and the Cohere fallback.
The database, the embedding model and Cohere are replaced by fakes."""
import pytest

from backend.services import retrieval_service as rs
from tests.helpers import make_chunk


def chunk(chunk_id, text, similarity=0.9, url="https://www.fnx.co.il/a"):
    return make_chunk(url=url, text=text, chunk_id=chunk_id, similarity=similarity)


@pytest.fixture
def db(monkeypatch):
    """Fake database. Set db.matches (what search returns) and db.rows (chunks that can be fetched by id)."""
    class FakeDb:
        matches: list[dict] = []
        rows: list[dict] = []
        searches: list[int] = []

    fake = FakeDb()
    fake.matches, fake.rows, fake.searches = [], [], []

    def search(vector, top_k):
        fake.searches.append(top_k)
        return list(fake.matches)

    monkeypatch.setattr(rs, "embed_question", lambda question: [0.0])
    monkeypatch.setattr(rs.vector_repository, "search", search)
    monkeypatch.setattr(rs.vector_repository, "get_chunks_by_ids",
                        lambda ids: [row for row in fake.rows if row["chunk_id"] in ids])
    return fake


# --- vector search ---

def test_no_matches_gives_an_empty_result(db):
    result = rs.retrieve("q", use_rerank=False)
    assert result.chunks == [] and result.found is False and result.best_score == 0.0


def test_chunks_below_the_threshold_are_dropped(db):
    db.matches = [chunk("p1-0", "good", 0.9), chunk("p2-0", "weak", 0.5)]
    result = rs.retrieve("q", use_rerank=False, threshold=0.8)
    assert [c["text"] for c in result.chunks] == ["good"]
    assert result.best_score == 0.9


def test_a_chunk_exactly_at_the_threshold_is_kept(db):
    db.matches = [chunk("p1-0", "on the line", 0.8)]
    assert rs.retrieve("q", use_rerank=False, threshold=0.8).found is True


def test_best_score_is_reported_even_when_nothing_passes(db):
    db.matches = [chunk("p1-0", "weak", 0.5)]
    result = rs.retrieve("q", use_rerank=False, threshold=0.8)
    assert result.found is False and result.best_score == 0.5


def test_results_are_sorted_best_first_and_limited_to_top_k(db):
    db.matches = [chunk(f"p{i}-0", f"text {i}", 0.8 + i / 100) for i in range(5)]
    result = rs.retrieve("q", top_k=2, use_rerank=False, threshold=0.0)
    assert [c["text"] for c in result.chunks] == ["text 4", "text 3"]


def test_the_database_is_asked_for_extra_chunks(db):
    rs.retrieve("q", top_k=4, use_rerank=False)
    assert db.searches == [4 * rs.FETCH_MULTIPLIER]


def test_identical_text_under_another_url_is_removed(db):
    db.matches = [
        chunk("p1-0", "same  text", 0.95, url="https://www.fnx.co.il/a"),
        chunk("p2-0", "same text", 0.90, url="https://www.fnx.co.il/b"),  # only the spaces differ
        chunk("p3-0", "other", 0.85),
    ]
    result = rs.retrieve("q", use_rerank=False, threshold=0.0)
    assert [c["url"] for c in result.chunks] == ["https://www.fnx.co.il/a", "https://www.fnx.co.il/a"]
    assert [c["similarity"] for c in result.chunks] == [0.95, 0.85]


# --- neighbor chunks ---

@pytest.mark.parametrize("chunk_id, expected", [
    ("abc-3", ["abc-4", "abc-5"]),
    ("a-b-c-9", ["a-b-c-10", "a-b-c-11"]),  # only the last dash counts
    ("abc-x", []),
    ("abc", []),
    ("-3", []),
])
def test_neighbor_ids(monkeypatch, chunk_id, expected):
    monkeypatch.setattr(rs, "NEIGHBOR_CHUNKS", 2)
    assert rs._neighbor_ids(chunk_id) == expected


def test_following_chunks_are_added_right_after_their_parent(db):
    db.matches = [chunk("p1-3", "parent", 0.9), chunk("p9-0", "other", 0.85)]
    db.rows = [chunk("p1-4", "after one"), chunk("p1-5", "after two")]
    result = rs.retrieve("q", use_rerank=False, threshold=0.0)
    assert [c["text"] for c in result.chunks] == ["parent", "after one", "after two", "other"]
    assert result.chunks[1]["similarity"] == 0.9  # it gets its parent's score


def test_a_missing_neighbor_is_not_a_problem(db):
    db.matches = [chunk("p1-3", "last chunk of the page", 0.9)]
    result = rs.retrieve("q", use_rerank=False, threshold=0.0)
    assert [c["text"] for c in result.chunks] == ["last chunk of the page"]


def test_a_neighbor_that_is_already_included_is_not_repeated(db):
    db.matches = [chunk("p1-0", "first", 0.95), chunk("p1-1", "second", 0.9)]
    db.rows = [chunk("p1-1", "second"), chunk("p1-2", "third")]
    result = rs.retrieve("q", use_rerank=False, threshold=0.0)
    texts = [c["text"] for c in result.chunks]
    assert sorted(texts) == ["first", "second", "third"]  # nothing repeated, nothing lost
    assert texts[0] == "first"


def test_only_the_best_parents_get_neighbors(db, monkeypatch):
    monkeypatch.setattr(rs, "NEIGHBOR_PARENTS", 1)
    db.matches = [chunk("p1-0", "best", 0.95), chunk("p2-0", "second", 0.9)]
    db.rows = [chunk("p1-1", "after best"), chunk("p2-1", "after second")]
    result = rs.retrieve("q", use_rerank=False, threshold=0.0)
    assert [c["text"] for c in result.chunks] == ["best", "after best", "second"]


# --- rerank ---

@pytest.fixture
def cohere(monkeypatch):
    """Fake reranker: scores each chunk by the number in its text. Set cohere.error to make it fail."""
    class FakeCohere:
        error = None

    fake = FakeCohere()

    def rerank(question, chunks, top_n):
        if fake.error:
            raise fake.error
        scored = [{**c, "rerank_score": float(c["text"])} for c in chunks]
        return sorted(scored, key=lambda c: c["rerank_score"], reverse=True)[:top_n]

    monkeypatch.setattr(rs.rerank_service, "rerank", rerank)
    return fake


def test_rerank_keeps_chunks_at_or_above_its_own_threshold(db, cohere):
    db.matches = [chunk("p1-0", "0.9"), chunk("p2-0", "0.6"), chunk("p3-0", "0.2")]
    result = rs.retrieve("q", use_rerank=True, threshold=0.5)
    assert [c["rerank_score"] for c in result.chunks] == [0.9, 0.6]
    assert result.best_score == 0.9


def test_a_reranked_chunk_exactly_at_the_threshold_is_kept(db, cohere):
    db.matches = [chunk("p1-0", "0.5")]
    assert rs.retrieve("q", use_rerank=True, threshold=0.5).found is True


def test_rerank_asks_the_database_for_the_rerank_amount(db, cohere):
    rs.retrieve("q", use_rerank=True)
    assert db.searches == [rs.RERANK_FETCH_K]


def test_rerank_failure_falls_back_to_vector_search(db, cohere):
    cohere.error = RuntimeError("trial limit")
    db.matches = [chunk("p1-0", "plain vector result", 0.9)]
    result = rs.retrieve("q", use_rerank=True, threshold=0.8)
    assert [c["text"] for c in result.chunks] == ["plain vector result"]


def test_rerank_with_no_candidates_is_empty(db, cohere):
    result = rs.retrieve("q", use_rerank=True)
    assert result.chunks == []


def test_rerank_setting_is_used_when_not_given(db, cohere, monkeypatch):
    monkeypatch.setattr(rs, "RERANK_ENABLED", True)
    db.matches = [chunk("p1-0", "0.9")]
    assert "rerank_score" in rs.retrieve("q").chunks[0]
