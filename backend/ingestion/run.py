"""One-command incremental pipeline: sitemap -> crawl -> chunk -> embed -> Supabase.

Run:
  python -m backend.ingestion.run --dry-run     show what would happen, change nothing
  python -m backend.ingestion.run               do the update
  python -m backend.ingestion.run --full        re-crawl every selected page (slower, safest)
  python -m backend.ingestion.run --max-pages N embed at most N pages in this run (daily quota)

Safe to run again: pages that are already up to date are skipped, and a run that stops
(quota, crash) continues where it stopped.
"""
import argparse
import asyncio
import json
import time
from urllib.parse import urlparse

from google.genai import errors

from backend.ingestion import config, scraper, state
from backend.ingestion.chunker import chunk_page
from backend.ingestion.embed_upload import upload_page
from backend.repositories import vector_repository


def load_page(url: str) -> dict:
    path = config.RAW_DIR / scraper.file_name_for(url)
    return json.loads(path.read_text(encoding="utf-8"))


def upload_with_quota_wait(chunks: list[dict]) -> None:
    """Upload one page. On a 429, wait a minute and try again (the limit is often per minute)."""
    for attempt in range(1, config.QUOTA_WAIT_ATTEMPTS + 1):
        try:
            upload_page(chunks)
            return
        except errors.APIError as error:
            if error.code != 429 or attempt == config.QUOTA_WAIT_ATTEMPTS:
                raise
            print(f"Too many requests. Waiting {config.QUOTA_WAIT_SECONDS}s (wait {attempt} of {config.QUOTA_WAIT_ATTEMPTS - 1})...")
            time.sleep(config.QUOTA_WAIT_SECONDS)


def main() -> None:
    parser = argparse.ArgumentParser(description="Incremental update of the chatbot data.")
    parser.add_argument("--dry-run", action="store_true", help="only show the plan")
    parser.add_argument("--full", action="store_true", help="re-crawl every selected page")
    parser.add_argument("--max-pages", type=int, help="embed at most N pages in this run")
    parser.add_argument("--tier", type=int, choices=sorted(config.PRIORITY_TIERS), help="work only on this priority tier")
    parser.add_argument("--sections", help="work only on these sections, comma separated (for example gemel,loans)")
    args = parser.parse_args()

    # Limit crawling and embedding to some sections. Removal checks always look at the whole site.
    only_sections = None
    if args.tier:
        only_sections = set(config.PRIORITY_TIERS[args.tier])
    if args.sections:
        only_sections = (only_sections or set()) | {name.strip() for name in args.sections.split(",") if name.strip()}

    def in_scope(url: str) -> bool:
        if only_sections is None:
            return True
        segments = [part for part in urlparse(url).path.split("/") if part]
        return bool(segments) and segments[0] in only_sections

    robots = scraper.load_robots()
    lastmods = scraper.load_lastmod_map()
    selected = scraper.select_urls(lastmods, robots)
    saved = state.load_saved_pages()
    db_hashes = vector_repository.list_page_hashes()

    print(f"Sitemap: {len(lastmods)} URLs, {len(selected)} selected. Saved: {len(saved)}. In database: {len(db_hashes)}.")

    if state.sitemap_looks_broken(len(selected), len(saved)):
        print("STOP: the sitemap has far fewer pages than we hold. Nothing was changed.")
        return

    plan = state.classify(selected, lastmods, saved, set(db_hashes), full=args.full)
    print(f"New: {len(plan.new)} | To re-check: {len(plan.check)} | Unchanged: {len(plan.unchanged)} | Gone from sitemap: {len(plan.removed)}")

    if args.dry_run:
        for label, urls in (("NEW", plan.new), ("RE-CHECK", plan.check), ("REMOVED?", plan.removed)):
            for url in urls[:20]:
                print(f"  {label}: {url}")
            if len(urls) > 20:
                print(f"  {label}: ... and {len(urls) - 20} more")
        print("Dry run: nothing was changed.")
        return

    # 1. Crawl new and possibly changed pages. Old copies stay if a crawl fails.
    to_crawl = [url for url in plan.new + plan.check if in_scope(url)]
    failed: list[str] = []
    if to_crawl:
        scraper_saved, _, _ = asyncio.run(scraper.scrape_pages(to_crawl, robots, lastmods, failed_urls=failed))
        print(f"Crawled: {scraper_saved} saved, {len(failed)} failed")

    # 2. Chunk every saved page (local and fast). Embed only the pages whose text changed
    #    or that are not in the database yet.
    added, updated, empty, unchanged = [], [], [], 0
    pending = []
    for url in selected:
        if not in_scope(url):
            continue
        if not (config.RAW_DIR / scraper.file_name_for(url)).exists():
            continue  # never crawled successfully
        chunks = chunk_page(load_page(url))
        if not chunks:
            empty.append(url)
        elif db_hashes.get(url) == chunks[0]["content_hash"]:
            unchanged += 1
        else:
            pending.append((url, chunks))

    quota_hit = False
    done = 0
    for url, chunks in pending:
        if args.max_pages is not None and done >= args.max_pages:
            break
        try:
            upload_with_quota_wait(chunks)
        except errors.APIError as error:
            if error.code == 429:
                quota_hit = True
                print("Gemini still says 429 after waiting. The daily quota is probably used. Stopping; run again later.")
                break
            print(f"FAILED to embed {url}: {error}")
            failed.append(url)
            continue
        (updated if url in db_hashes else added).append(url)
        done += 1
        print(f"Uploaded ({done}/{len(pending)}): {url}")
        time.sleep(config.PAGE_PAUSE_SECONDS)

    # 3. Remove pages that are gone. A page missing from the sitemap is deleted only if the
    #    website itself says 404/410.
    to_delete, to_keep = state.split_removed(plan.removed, lastmods)
    for url in to_delete:
        vector_repository.delete_by_url(url)
        (config.RAW_DIR / scraper.file_name_for(url)).unlink(missing_ok=True)

    # 4. Report.
    print("\n=== REPORT ===")
    print(f"Added: {len(added)} | Updated: {len(updated)} | Unchanged: {unchanged} | Removed: {len(to_delete)}")
    print(f"Failed: {len(failed)} | Empty pages: {len(empty)} | Kept (not in sitemap but still online): {len(to_keep)}")
    left = len(pending) - done
    if left > 0:
        print(f"Still waiting to be embedded: {left} pages{' (quota)' if quota_hit else ''}. Run again to continue.")
    for label, urls in (("ADDED", added), ("UPDATED", updated), ("REMOVED", to_delete), ("FAILED", failed), ("KEPT", to_keep)):
        for url in urls:
            print(f"  {label}: {url}")


if __name__ == "__main__":
    main()
