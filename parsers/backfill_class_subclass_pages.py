"""Targeted backfill for dedicated class subclass pages.

This script fetches subclass pages linked from each core `<class>:main` page and
stores them into `dnd2024_data.json` under the `class_subclasses` key.
"""

from __future__ import annotations

import json
import re
import time
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import URLError, HTTPError
from urllib.request import Request, urlopen


BASE_URL = "http://dnd2024.wikidot.com"
ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = ROOT / "dnd2024_data.json"

CORE_CLASS_SLUGS = [
    "artificer",
    "barbarian",
    "bard",
    "cleric",
    "druid",
    "fighter",
    "monk",
    "paladin",
    "ranger",
    "rogue",
    "sorcerer",
    "warlock",
    "wizard",
]

NON_SUBCLASS_PAGE_SUFFIXES = {
    "main",
    "spell-list",
    "metamagic",
    "eldritch-invocation",
}


class _PageContentParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_title = False
        self.title_text: list[str] = []

        self.in_page_content = False
        self.content_depth = 0
        self.content_parts: list[str] = []

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)

        if tag == "title":
            self.in_title = True

        if tag == "div" and attrs_dict.get("id") == "page-content":
            self.in_page_content = True
            self.content_depth = 1
            return

        if self.in_page_content:
            if tag == "div":
                self.content_depth += 1
            if tag in {"p", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6", "br"}:
                self.content_parts.append("\n")

    def handle_endtag(self, tag):
        if tag == "title":
            self.in_title = False

        if self.in_page_content and tag == "div":
            self.content_depth -= 1
            if self.content_depth <= 0:
                self.in_page_content = False

        if self.in_page_content and tag in {
            "p",
            "li",
            "tr",
            "h1",
            "h2",
            "h3",
            "h4",
            "h5",
            "h6",
        }:
            self.content_parts.append("\n")

    def handle_data(self, data):
        text = unescape(data)
        if self.in_title:
            self.title_text.append(text)
        if self.in_page_content:
            self.content_parts.append(text)

    def parsed_title(self) -> str:
        raw = "".join(self.title_text).strip()
        if " - " in raw:
            return raw.split(" - ", 1)[0].strip()
        return raw

    def parsed_content(self) -> str:
        raw = "".join(self.content_parts)
        lines = [re.sub(r"\s+", " ", ln).strip() for ln in raw.split("\n")]
        lines = [ln for ln in lines if ln]
        return "\n".join(lines)


def fetch_html(url: str, timeout: int = 20) -> str:
    req = Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; VibeDnD/1.0)"})
    with urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="ignore")


def extract_subclass_urls_from_main(html: str, class_slug: str) -> list[str]:
    pattern = rf'href="/({re.escape(class_slug)}:[^"#?]+)"'
    found = re.findall(pattern, html)
    urls = []
    for url_part in found:
        suffix = url_part.split(":", 1)[1]
        if suffix in NON_SUBCLASS_PAGE_SUFFIXES:
            continue
        urls.append(f"{BASE_URL}/{url_part}")
    return sorted(set(urls))


def parse_entry_from_html(url: str, html: str) -> dict:
    parser = _PageContentParser()
    parser.feed(html)
    return {
        "title": parser.parsed_title() or "Unknown",
        "url": url,
        "content": parser.parsed_content(),
    }


def main():
    if not DATA_FILE.exists():
        raise FileNotFoundError(f"Raw data file not found: {DATA_FILE}")

    with DATA_FILE.open("r", encoding="utf-8") as f:
        raw = json.load(f)

    subclass_urls: list[str] = []
    for class_slug in CORE_CLASS_SLUGS:
        main_url = f"{BASE_URL}/{class_slug}:main"
        print(f"Scanning {main_url}")
        try:
            html = fetch_html(main_url)
        except (URLError, HTTPError) as exc:
            print(f"  Failed: {exc}")
            continue

        urls = extract_subclass_urls_from_main(html, class_slug)
        print(f"  Found {len(urls)} subclass links")
        subclass_urls.extend(urls)
        time.sleep(0.25)

    subclass_urls = sorted(set(subclass_urls))
    print(f"Total unique subclass pages: {len(subclass_urls)}")

    entries = []
    for i, url in enumerate(subclass_urls, start=1):
        print(f"[{i}/{len(subclass_urls)}] Fetching {url}")
        try:
            html = fetch_html(url)
        except (URLError, HTTPError) as exc:
            print(f"  Failed: {exc}")
            continue
        entries.append(parse_entry_from_html(url, html))
        time.sleep(0.25)

    raw["class_subclasses"] = entries
    with DATA_FILE.open("w", encoding="utf-8") as f:
        json.dump(raw, f, indent=2, ensure_ascii=False)

    print(f"Saved {len(entries)} class subclass entries to {DATA_FILE}")


if __name__ == "__main__":
    main()
