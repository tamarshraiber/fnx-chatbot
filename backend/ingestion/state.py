"""Compare the sitemap with the pages we already hold (no network, no database here)."""
import json
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Callable

from backend.ingestion import config


@dataclass
class Plan:
    new: list[str] = field(default_factory=list)  # in the sitemap, never saved
    check: list[str] = field(default_factory=list)  # saved, but the sitemap lastmod changed
    unchanged: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)  # saved or in the database, not in the sitemap


def load_saved_pages() -> dict[str, dict]:
    """Read data/raw and return {url: {"lastmod": ..., "content_hash": ...}}."""
    saved = {}
    for path in config.RAW_DIR.glob("*.json"):
        page = json.loads(path.read_text(encoding="utf-8"))
        saved[page["url"]] = {"lastmod": page.get("lastmod", ""), "content_hash": page.get("content_hash", "")}
    return saved


def classify(
    selected: list[str],
    sitemap_lastmods: dict[str, str],
    saved: dict[str, dict],
    db_urls: set[str],
    full: bool = False,
) -> Plan:
    """Sort pages into new / check (maybe changed) / unchanged / removed."""
    plan = Plan()
    for url in selected:
        if url not in saved:
            plan.new.append(url)
        elif full:
            plan.check.append(url)
        else:
            sitemap_lastmod = sitemap_lastmods.get(url, "")
            # No date in the sitemap means we cannot tell, so we keep the saved copy.
            if sitemap_lastmod and sitemap_lastmod != saved[url]["lastmod"]:
                plan.check.append(url)
            else:
                plan.unchanged.append(url)
    selected_set = set(selected)
    plan.removed = sorted((set(saved) | db_urls) - selected_set)
    return plan


def sitemap_looks_broken(selected_count: int, saved_count: int) -> bool:
    """True if the sitemap gives far fewer pages than we hold. Then we must not delete anything."""
    return saved_count > 0 and selected_count < saved_count * config.SAFETY_MIN_RATIO


def is_gone(url: str) -> bool:
    """True only if the website itself answers 404 or 410 for this page."""
    request = urllib.request.Request(url, headers={"User-Agent": config.USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=30):
            return False  # the page still loads
    except urllib.error.HTTPError as error:
        return error.code in (404, 410)
    except Exception:
        return False  # network problem or a filter block: not proof, so keep the page


def split_removed(
    removed: list[str],
    sitemap_lastmods: dict[str, str],
    gone_check: Callable[[str], bool] = is_gone,
) -> tuple[list[str], list[str]]:
    """Return (to_delete, to_keep).

    A page that is still in the sitemap but outside our scope is deleted directly.
    A page that vanished from the sitemap is deleted only if the website really says 404/410.
    """
    to_delete, to_keep = [], []
    for url in removed:
        if url in sitemap_lastmods or gone_check(url):
            to_delete.append(url)
        else:
            to_keep.append(url)
    return to_delete, to_keep
