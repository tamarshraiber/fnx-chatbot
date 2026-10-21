"""Shared setup for all tests. No test here calls a real LLM, database or website."""
import pytest

from backend.services import llm_service
from backend.utils import answer_cache, rate_limit


@pytest.fixture(autouse=True)
def clean_state():
    """The cache, the rate limit and the provider cooldowns live in memory. Start every test with them empty."""
    answer_cache._store.clear()
    rate_limit._recent.clear()
    llm_service._blocked_until.clear()
    yield
    answer_cache._store.clear()
    rate_limit._recent.clear()
    llm_service._blocked_until.clear()

