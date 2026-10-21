"""Ingestion: cleaning and chunking page text, and deciding which pages are new, changed or removed.
Nothing here touches the network or the database."""
import json
import urllib.error

import pytest

from backend.ingestion import chunker, config, curated, state

SIZE = config.CHUNK_SIZE
MIN = config.MIN_CHUNK_SIZE


def page(markdown, url="https://www.fnx.co.il/test/", title="כותרת"):
    return {"url": url, "title": title, "lastmod": "2026-01-01", "markdown": markdown, "crawled_at": "2026-02-01"}


# --- clean_markdown ---

def test_cookie_banner_is_removed():
    text = chunker.clean_markdown("לפני\nשימוש בקבצי Cookies באתר\nעוד שורה\nסגירה\nאחרי")
    assert "Cookies" not in text and "לפני" in text and "אחרי" in text


def test_images_are_removed_completely():
    assert chunker.clean_markdown("טקסט ![לוגו](https://x/y.png) וסוף") == "טקסט  וסוף"


def test_links_keep_only_their_text():
    assert chunker.clean_markdown("ראו [את הטופס](https://x/form \"title\") כאן") == "ראו את הטופס כאן"


@pytest.mark.parametrize("marker", chunker.FOOTER_MARKERS)
def test_everything_after_the_footer_is_cut(marker):
    text = chunker.clean_markdown(f"תוכן חשוב\n\n{marker}\nטלפון בפוטר")
    assert text == "תוכן חשוב"


def test_blank_lines_and_trailing_spaces_are_tidied():
    assert chunker.clean_markdown("א   \n\n\n\n\nב  \n") == "א\n\nב"


# --- split_into_sections ---

def test_text_is_cut_before_each_heading():
    sections = chunker.split_into_sections("# א\nשורה\n## ב\nעוד\n### ג")
    assert sections == ["# א\nשורה", "## ב\nעוד", "### ג"]


def test_a_heading_inside_a_list_item_also_starts_a_section():
    sections = chunker.split_into_sections("# מוקדים\n  * ## מוקד שירות\n  טלפון 1\n- ## מוקד תביעות\n  טלפון 2")
    assert len(sections) == 3 and sections[1].startswith("* ## מוקד שירות")


def test_text_before_the_first_heading_is_kept():
    assert chunker.split_into_sections("פתיח\n# כותרת\nגוף") == ["פתיח", "# כותרת\nגוף"]


def test_a_hash_that_is_not_a_heading_does_not_split():
    assert len(chunker.split_into_sections("# א\nמספר #5 בתור\n#hashtag")) == 1


def test_empty_text_has_no_sections():
    assert chunker.split_into_sections("") == []


# --- hard_split / split_long_section ---

def test_hard_split_cuts_at_a_space():
    parts = chunker.hard_split("aaa bbb ccc ddd", 8)
    assert parts == ["aaa bbb", "ccc ddd"]


def test_hard_split_cuts_a_line_without_spaces_at_the_size():
    assert chunker.hard_split("x" * 25, 10) == ["x" * 10, "x" * 10, "x" * 5]


def test_a_short_section_is_not_split():
    assert chunker.split_long_section("קצר") == ["קצר"]


def test_a_long_section_is_split_into_pieces_that_fit():
    section = "\n".join(f"שורה מספר {i} " + "מילה " * 10 for i in range(60))
    pieces = chunker.split_long_section(section)
    assert len(pieces) > 1
    # A piece may be as big as CHUNK_SIZE plus the overlap that starts the next piece.
    assert all(len(piece) <= SIZE + config.CHUNK_OVERLAP + 1 for piece in pieces)


def test_pieces_overlap_and_lose_no_line():
    lines = [f"שורה {i} " + "א" * 60 for i in range(40)]
    pieces = chunker.split_long_section("\n".join(lines))
    joined = "\n".join(pieces)
    assert all(line in joined for line in lines)
    tail = pieces[0][-config.CHUNK_OVERLAP:]
    assert pieces[1].startswith(tail)


def test_a_single_huge_line_is_cut_too():
    pieces = chunker.split_long_section("מילה " * 500)
    assert len(pieces) > 1 and all(len(piece) <= SIZE + config.CHUNK_OVERLAP + 1 for piece in pieces)


# --- merge_small_pieces ---

def test_a_small_piece_is_merged_into_the_next_one():
    small, big = "א" * 50, "ב" * 300
    assert chunker.merge_small_pieces([small, big]) == [f"{small}\n{big}"]


def test_a_merge_never_goes_over_the_size_limit():
    small, big = "א" * 50, "ב" * (SIZE - 10)
    assert chunker.merge_small_pieces([small, big]) == [small, big]


def test_a_tiny_last_piece_joins_the_one_before():
    big, tiny = "א" * 300, "ב" * 20
    assert chunker.merge_small_pieces([big, tiny]) == [f"{big}\n{tiny}"]


def test_big_pieces_are_left_alone():
    pieces = ["א" * 300, "ב" * 300, "ג" * 300]
    assert chunker.merge_small_pieces(pieces) == pieces


def test_a_single_tiny_piece_is_kept():
    assert chunker.merge_small_pieces(["קצר"]) == ["קצר"]


def test_nothing_in_nothing_out():
    assert chunker.merge_small_pieces([]) == []


# --- chunk_page ---

LONG_BODY = "# נושא\n" + "\n".join(f"שורה {i} " + "מילה " * 20 for i in range(30))


def test_chunk_records_have_the_right_fields():
    chunks = chunker.chunk_page(page(LONG_BODY))
    assert len(chunks) > 1
    for index, chunk in enumerate(chunks):
        assert chunk["chunk_index"] == index
        assert chunk["chunk_id"].endswith(f"-{index}")
        assert chunk["url"] == "https://www.fnx.co.il/test/" and chunk["lastmod"] == "2026-01-01"
        assert chunk["crawled_at"] == "2026-02-01"
        assert chunk["text"].startswith("כותרת\n\n")  # the title helps the embedding know the topic
    assert len({chunk["chunk_id"] for chunk in chunks}) == len(chunks)


def test_chunk_ids_depend_on_the_url_only():
    first = chunker.chunk_page(page(LONG_BODY, url="https://www.fnx.co.il/one/"))
    again = chunker.chunk_page(page(LONG_BODY + "\nשורה חדשה", url="https://www.fnx.co.il/one/"))
    other = chunker.chunk_page(page(LONG_BODY, url="https://www.fnx.co.il/two/"))
    assert first[0]["chunk_id"] == again[0]["chunk_id"]
    assert first[0]["chunk_id"] != other[0]["chunk_id"]


def test_content_hash_changes_only_when_the_useful_text_changes():
    base = chunker.chunk_page(page("# א\nתוכן"))[0]["content_hash"]
    same_with_noise = chunker.chunk_page(page("# א\nתוכן\n\n\n\n![img](x.png)"))[0]["content_hash"]
    changed = chunker.chunk_page(page("# א\nתוכן אחר"))[0]["content_hash"]
    assert base == same_with_noise and base != changed


def test_every_chunk_of_a_page_shares_the_same_hash():
    assert len({chunk["content_hash"] for chunk in chunker.chunk_page(page(LONG_BODY))}) == 1


def test_footer_text_never_reaches_a_chunk():
    chunks = chunker.chunk_page(page("# א\nתוכן\n## כל הדרכים לדבר איתנו\nפוטר"))
    assert all("פוטר" not in chunk["text"] for chunk in chunks)


def test_a_missing_crawled_at_is_allowed():
    raw = page("# א\nתוכן")
    del raw["crawled_at"]
    assert chunker.chunk_page(raw)[0]["crawled_at"] is None


def test_curated_chunks_come_first(monkeypatch):
    monkeypatch.setitem(curated.CURATED_CHUNKS, "https://www.fnx.co.il/test/", ["סיכום ידני"])
    chunks = chunker.chunk_page(page("# א\nתוכן"))
    assert chunks[0]["text"].endswith("סיכום ידני") and chunks[0]["chunk_index"] == 0
    assert "תוכן" in chunks[1]["text"]


# --- state.classify ---

def saved(lastmod="2026-01-01"):
    return {"lastmod": lastmod, "content_hash": "h"}


def test_classify_sorts_pages_into_groups():
    plan = state.classify(
        selected=["new", "changed", "same", "nodate"],
        sitemap_lastmods={"new": "2026-03-01", "changed": "2026-03-01", "same": "2026-01-01"},
        saved={"changed": saved(), "same": saved(), "nodate": saved(), "gone": saved()},
        db_urls={"in_db_only"},
    )
    assert plan.new == ["new"]
    assert plan.check == ["changed"]
    assert plan.unchanged == ["same", "nodate"]  # no sitemap date: keep the saved copy
    assert plan.removed == ["gone", "in_db_only"]


def test_full_mode_checks_every_saved_page():
    plan = state.classify(["a", "b"], {"a": "2026-01-01"}, {"a": saved(), "b": saved()}, set(), full=True)
    assert plan.check == ["a", "b"] and plan.unchanged == []


def test_full_mode_still_treats_unknown_pages_as_new():
    assert state.classify(["a"], {}, {}, set(), full=True).new == ["a"]


def test_nothing_to_do():
    plan = state.classify([], {}, {}, set())
    assert plan.new == plan.check == plan.unchanged == plan.removed == []


# --- safety checks ---

@pytest.mark.parametrize("selected, held, broken", [
    (100, 100, False),
    (50, 100, False),   # exactly at the ratio is fine
    (49, 100, True),    # far fewer pages than we hold
    (0, 100, True),     # an empty sitemap must never delete everything
    (0, 0, False),      # first run
    (5, 0, False),
])
def test_sitemap_looks_broken(selected, held, broken):
    assert state.sitemap_looks_broken(selected, held) is broken


def test_a_page_in_the_sitemap_but_out_of_scope_is_deleted_without_asking_the_site():
    def must_not_be_called(url):
        raise AssertionError("website was asked")
    assert state.split_removed(["a"], {"a": "2026-01-01"}, must_not_be_called) == (["a"], [])


def test_a_vanished_page_is_deleted_only_if_the_site_says_it_is_gone():
    gone = {"x": True, "y": False}
    to_delete, to_keep = state.split_removed(["x", "y"], {}, lambda url: gone[url])
    assert to_delete == ["x"] and to_keep == ["y"]


# --- is_gone ---

class OkPage:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def fake_urlopen(monkeypatch, result):
    def urlopen(request, timeout):
        if isinstance(result, Exception):
            raise result
        return result
    monkeypatch.setattr(state.urllib.request, "urlopen", urlopen)


def http_error(code):
    return urllib.error.HTTPError("https://x", code, "msg", {}, None)


def test_a_page_that_loads_is_not_gone(monkeypatch):
    fake_urlopen(monkeypatch, OkPage())
    assert state.is_gone("https://x") is False


@pytest.mark.parametrize("code, gone", [(404, True), (410, True), (403, False), (429, False), (500, False)])
def test_only_404_and_410_mean_gone(monkeypatch, code, gone):
    fake_urlopen(monkeypatch, http_error(code))
    assert state.is_gone("https://x") is gone


def test_a_network_problem_is_not_proof_that_the_page_is_gone(monkeypatch):
    fake_urlopen(monkeypatch, TimeoutError("slow"))
    assert state.is_gone("https://x") is False


# --- load_saved_pages ---

def test_saved_pages_are_read_from_the_raw_folder(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "RAW_DIR", tmp_path)
    (tmp_path / "1.json").write_text(json.dumps({"url": "u1", "lastmod": "d1", "content_hash": "h1"}), encoding="utf-8")
    (tmp_path / "2.json").write_text(json.dumps({"url": "u2"}), encoding="utf-8")  # old file without dates
    assert state.load_saved_pages() == {
        "u1": {"lastmod": "d1", "content_hash": "h1"},
        "u2": {"lastmod": "", "content_hash": ""},
    }
