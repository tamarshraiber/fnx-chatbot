"""Test the step 13 comparison logic with fake data (no network, no database).

Run:  python -m scripts.check_pipeline
"""
from backend.ingestion import state


def check(name: str, condition: bool) -> None:
    print(f"{'OK  ' if condition else 'FAIL'} {name}")
    if not condition:
        raise SystemExit(1)


def main() -> None:
    selected = ["a", "b", "c", "d"]
    lastmods = {"a": "2026-01-01", "b": "2026-02-02", "c": "2026-01-01", "d": "2026-03-03", "x": "2026-01-01"}
    saved = {
        "a": {"lastmod": "2026-01-01", "content_hash": "h"},  # same date -> unchanged
        "b": {"lastmod": "2026-01-01", "content_hash": "h"},  # newer date -> re-check
        "c": {"lastmod": "2026-01-01", "content_hash": "h"},  # same date -> unchanged
        "x": {"lastmod": "2026-01-01", "content_hash": "h"},  # in sitemap, out of scope
        "gone": {"lastmod": "2026-01-01", "content_hash": "h"},  # not in sitemap
    }
    plan = state.classify(selected, lastmods, saved, db_urls={"a", "dbonly"})

    check("new page found", plan.new == ["d"])
    check("changed lastmod is re-checked", plan.check == ["b"])
    check("same lastmod is unchanged", plan.unchanged == ["a", "c"])
    check("removed includes saved and database-only pages", plan.removed == ["dbonly", "gone", "x"])

    full_plan = state.classify(selected, lastmods, saved, db_urls=set(), full=True)
    check("--full re-checks every saved page", full_plan.check == ["a", "b", "c"])

    # Removal: "x" is still in the sitemap (out of scope) -> delete. Others need a real 404.
    to_delete, to_keep = state.split_removed(plan.removed, lastmods, gone_check=lambda url: url == "gone")
    check("out-of-scope page is deleted", "x" in to_delete)
    check("page with 404 is deleted", "gone" in to_delete)
    check("page that is still online is kept", to_keep == ["dbonly"])

    check("broken sitemap is detected", state.sitemap_looks_broken(selected_count=10, saved_count=100))
    check("normal sitemap is accepted", not state.sitemap_looks_broken(selected_count=95, saved_count=100))
    check("empty start is accepted", not state.sitemap_looks_broken(selected_count=0, saved_count=0))

    print("\nAll checks passed.")


if __name__ == "__main__":
    main()
