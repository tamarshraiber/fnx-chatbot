import asyncio
import hashlib
import json
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from urllib.robotparser import RobotFileParser

from crawl4ai import AsyncWebCrawler, BrowserConfig, CacheMode, CrawlerRunConfig

from backend.ingestion import config


def load_robots() -> RobotFileParser:
    """Download robots.txt so we can check which pages we are allowed to fetch."""
    request = urllib.request.Request(config.ROBOTS_URL, headers={"User-Agent": config.USER_AGENT})
    with urllib.request.urlopen(request, timeout=30) as response:
        lines = response.read().decode("utf-8").splitlines()
    parser = RobotFileParser()
    parser.parse(lines)
    return parser


def load_lastmod_map() -> dict[str, str]:
    """Read the sitemap and return {page url: lastmod date}."""
    request = urllib.request.Request(config.SITEMAP_URL, headers={"User-Agent": config.USER_AGENT})
    with urllib.request.urlopen(request, timeout=60) as response:
        root = ET.fromstring(response.read())
    namespace = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    result = {}
    for node in root.findall("s:url", namespace):
        loc = node.findtext("s:loc", default="", namespaces=namespace).strip()
        lastmod = node.findtext("s:lastmod", default="", namespaces=namespace).strip()
        if loc:
            result[loc] = lastmod
    return result


def file_name_for(url: str) -> str:
    """Short, safe file name from the URL (Hebrew URLs make bad file names)."""
    return hashlib.sha256(url.encode("utf-8")).hexdigest()[:16] + ".json"


def build_run_config() -> CrawlerRunConfig:
    """Crawl4AI settings: always fetch fresh, drop menu/footer/header tags."""
    return CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        excluded_tags=["nav", "footer", "header", "aside", "form"],
        remove_overlay_elements=True,
        page_timeout=60000,
    )


async def scrape_pages(urls: list[str]) -> tuple[int, int]:
    """Fetch each URL and save it. Returns (saved_count, failed_count)."""
    robots = load_robots()
    lastmods = load_lastmod_map()
    config.RAW_DIR.mkdir(parents=True, exist_ok=True)

    saved = 0
    failed = 0
    browser_config = BrowserConfig(headless=True, user_agent=config.USER_AGENT)

    async with AsyncWebCrawler(config=browser_config) as crawler:
        for url in urls:
            if not robots.can_fetch(config.USER_AGENT, url):
                print(f"SKIP (blocked by robots.txt): {url}")
                failed += 1
                continue

            try:
                result = await crawler.arun(url=url, config=build_run_config())
                if not result.success:
                    raise RuntimeError(result.error_message or "unknown crawl error")

                markdown = str(result.markdown or "").strip()
                if not markdown:
                    raise RuntimeError("page has no text")

                page = {
                    "url": url,
                    "title": (result.metadata or {}).get("title", ""),
                    "markdown": markdown,
                    "lastmod": lastmods.get(url, ""),
                    "content_hash": hashlib.sha256(markdown.encode("utf-8")).hexdigest(),
                    "crawled_at": datetime.now(timezone.utc).isoformat(),
                }
                path = config.RAW_DIR / file_name_for(url)
                path.write_text(json.dumps(page, ensure_ascii=False, indent=2), encoding="utf-8")
                print(f"OK ({len(markdown)} chars): {url}")
                saved += 1
            except Exception as error:
                print(f"FAILED: {url} -> {error}")
                failed += 1

            await asyncio.sleep(config.DELAY_SECONDS)

    return saved, failed


def main() -> None:
    saved, failed = asyncio.run(scrape_pages(config.TEST_URLS))
    print(f"\n{saved} saved, {failed} failed")


if __name__ == "__main__":
    main()
