"""The public /stats numbers: totals only, cached, and still available when the database is down."""
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.services import stats_service

client = TestClient(app)

DATA = {"pages": 1064, "chunks": 5000, "last_refresh": "2026-10-20T03:00:00+00:00"}


@pytest.fixture(autouse=True)
def empty_cache():
    stats_service._cache.update(time=0.0, data=None)
    yield
    stats_service._cache.update(time=0.0, data=None)


def test_stats_have_the_database_numbers_and_the_eval_scores(monkeypatch):
    monkeypatch.setattr(stats_service.vector_repository, "get_stats", lambda: DATA)
    body = client.get("/stats").json()
    assert body["pages"] == 1064
    assert body["eval"]["answerable_total"] == 20


def test_stats_are_cached(monkeypatch):
    calls = []
    monkeypatch.setattr(stats_service.vector_repository, "get_stats", lambda: calls.append(1) or DATA)
    client.get("/stats")
    client.get("/stats")
    assert len(calls) == 1


def test_stats_still_answer_when_the_database_is_down(monkeypatch):
    def broken():
        raise RuntimeError("down")

    monkeypatch.setattr(stats_service.vector_repository, "get_stats", broken)
    response = client.get("/stats")
    assert response.status_code == 200
    assert response.json()["pages"] is None
    assert response.json()["eval"] is not None
    assert stats_service._cache["data"] is None  # a failed answer is not remembered


def test_stats_contain_no_user_data(monkeypatch):
    monkeypatch.setattr(stats_service.vector_repository, "get_stats", lambda: DATA)
    assert set(client.get("/stats").json()) == {"pages", "chunks", "last_refresh", "eval"}
