import json
import time
from urllib.parse import unquote

import requests
from bs4 import BeautifulSoup

BASE_URL = "http://dnd2024.wikidot.com"

# All known category index pages
CATEGORIES = {
    "spells": "spell:all",
    "classes": "class:all",
    "feats": "feat:all",
    "species": "species:all",
    "backgrounds": "background:all",
    "ua": "ua:all",
}

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

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; DnD2024Scraper/1.0)"}
FEAT_FAMILY_HEADINGS = {
    "Origin Feats",
    "General Feats",
    "Fighting Style Feats",
    "Epic Boon Feats",
    "Dragonmark Feats",
}


def fetch(url, retries=3, delay=1.5):
    """Fetch a URL with retries and polite delay."""
    for attempt in range(retries):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=10)
            resp.raise_for_status()
            time.sleep(delay)  # Be polite — don't hammer the server
            return resp.text
        except requests.RequestException as e:
            print(f"  Attempt {attempt + 1} failed for {url}: {e}")
            time.sleep(delay * 2)
    return None


def _is_internal_wiki_link(href: str) -> bool:
    return href.startswith("/") and ":" in href and not href.startswith("//")


def _normalize_heading_text(text: str) -> str:
    return " ".join(str(text or "").strip().rstrip(":").split())


def _extract_page_tags(soup: BeautifulSoup) -> list[str]:
    tags = []
    seen = set()

    for link in soup.select("a[href*='/system:page-tags/tag/']"):
        href = str(link.get("href", "")).strip()
        if not href:
            continue

        tag = unquote(href.rstrip("/").rsplit("/", 1)[-1]).split("#")[0].strip()
        if not tag or tag in seen:
            continue

        seen.add(tag)
        tags.append(tag)

    return tags


def _get_feat_links_from_index(content) -> list[dict]:
    """Scrape feat links while preserving the visible family heading from feat:all."""
    links = []
    current_family_heading = None

    for element in content.find_all(
        ["h1", "h2", "h3", "h4", "h5", "h6", "strong", "b", "a"]
    ):
        if element.name == "a":
            href = str(element.get("href", ""))
            if not href.startswith("/feat:") or href.startswith("//") or href == "/feat:all":
                continue
            links.append(
                {
                    "name": element.get_text(strip=True),
                    "url": BASE_URL + href,
                    "feat_family_heading": current_family_heading,
                }
            )
            continue

        heading_text = _normalize_heading_text(element.get_text(" ", strip=True))
        if heading_text in FEAT_FAMILY_HEADINGS:
            current_family_heading = heading_text

    seen = set()
    unique = []
    for link in links:
        if link["url"] in seen:
            continue
        seen.add(link["url"])
        unique.append(link)

    return unique


def get_links_from_index(category_path):
    """Scrape all entry links from a category index page."""
    url = f"{BASE_URL}/{category_path}"
    print(f"Fetching index: {url}")
    html = fetch(url)
    if not html:
        return []

    soup = BeautifulSoup(html, "html.parser")
    content = soup.find(id="page-content")
    if not content:
        return []

    if category_path == "feat:all":
        return _get_feat_links_from_index(content)

    links = []
    for a in content.find_all("a", href=True):
        href = str(a.get("href", ""))
        # Only include internal wiki page links
        if _is_internal_wiki_link(href):
            full_url = BASE_URL + href
            links.append({"name": a.get_text(strip=True), "url": full_url})

    # Deduplicate by URL
    seen = set()
    unique = []
    for link in links:
        if link["url"] not in seen:
            seen.add(link["url"])
            unique.append(link)

    return unique


def scrape_entry(url, extra_fields=None):
    """Scrape the main content from a single entry page."""
    html = fetch(url)
    if not html:
        return None

    soup = BeautifulSoup(html, "html.parser")

    title = soup.find(id="page-title")
    title_text = title.get_text(strip=True) if title else "Unknown"

    content = soup.find(id="page-content")
    content_text = content.get_text(separator="\n", strip=True) if content else ""
    page_tags = _extract_page_tags(soup)

    entry = {
        "title": title_text,
        "url": url,
        "content": content_text,
    }
    if page_tags:
        entry["page_tags"] = page_tags
    if extra_fields:
        entry.update(extra_fields)
    return entry


def _extract_class_subclass_links_from_main(class_slug):
    """Extract subclass page links from <class>:main page content."""
    main_url = f"{BASE_URL}/{class_slug}:main"
    html = fetch(main_url)
    if not html:
        return []

    soup = BeautifulSoup(html, "html.parser")
    content = soup.find(id="page-content")
    if not content:
        return []

    links = []
    prefix = f"/{class_slug}:"
    for a in content.find_all("a", href=True):
        href = str(a.get("href", ""))
        if not href.startswith(prefix):
            continue
        suffix = href.split(":", 1)[1]
        if suffix in NON_SUBCLASS_PAGE_SUFFIXES:
            continue
        links.append(BASE_URL + href)

    return sorted(set(links))


def scrape_class_subclasses():
    """Scrape dedicated subclass pages linked from core class main pages."""
    all_urls = []
    for class_slug in CORE_CLASS_SLUGS:
        urls = _extract_class_subclass_links_from_main(class_slug)
        print(f"  {class_slug}: found {len(urls)} subclass links")
        all_urls.extend(urls)

    unique_urls = sorted(set(all_urls))
    print(f"  Total unique class subclass pages: {len(unique_urls)}")

    entries = []
    for i, url in enumerate(unique_urls):
        print(f"  [{i + 1}/{len(unique_urls)}] Scraping subclass page: {url}")
        entry = scrape_entry(url)
        if entry:
            entries.append(entry)

    return entries


def main():
    all_data = {}

    for category, path in CATEGORIES.items():
        print(f"\n=== Scraping category: {category} ===")
        links = get_links_from_index(path)
        print(f"  Found {len(links)} entries")

        entries = []
        for i, link in enumerate(links):
            print(f"  [{i + 1}/{len(links)}] Scraping: {link['name']} — {link['url']}")
            extra_fields = {
                key: value
                for key, value in link.items()
                if key not in {"name", "url"} and value is not None
            }
            entry = scrape_entry(link["url"], extra_fields=extra_fields)
            if entry:
                entries.append(entry)

        all_data[category] = entries
        print(f"  Done: {len(entries)} entries scraped for {category}")

    print("\n=== Scraping class subclass pages ===")
    class_subclasses = scrape_class_subclasses()
    all_data["class_subclasses"] = class_subclasses
    print(f"  Done: {len(class_subclasses)} class subclass pages scraped")

    # Save to JSON
    output_file = "dnd2024_data.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(all_data, f, indent=2, ensure_ascii=False)

    total = sum(len(v) for v in all_data.values())
    print(f"\nDone! {total} total entries saved to {output_file}")


if __name__ == "__main__":
    main()
