import json
import logging
import time
from pathlib import Path

from backend.repositories import vector_repository

logger = logging.getLogger(__name__)

STATS_FILE = Path(__file__).resolve().parent.parent / "stats.json"
CACHE_SECONDS = 600  # the numbers change only when the data is refreshed, so the database is asked rarely

_cache: dict = {"time": 0.0, "data": None}


def _eval_scores() -> dict | None:
    """The latest evaluation scores. They are saved in the repository by scripts/eval_e2e.py."""
    try:
        return json.loads(STATS_FILE.read_text(encoding="utf-8")).get("eval")
    except (OSError, ValueError):
        return None


def get_public_stats() -> dict:
    """Totals only: no question, answer or user data is ever part of this."""
    now = time.time()
    if _cache["data"] is not None and now - _cache["time"] < CACHE_SECONDS:
        return _cache["data"]

    try:
        data_stats = vector_repository.get_stats()
    except Exception as error:  # the page must still open when the database is down
        logger.warning(f"stats: database not reachable ({type(error).__name__})")
        data_stats = {"pages": None, "chunks": None, "last_refresh": None}

    stats = {**data_stats, "eval": _eval_scores()}
    if data_stats["pages"] is not None:  # do not keep a failed answer in the cache
        _cache.update(time=now, data=stats)
    return stats
