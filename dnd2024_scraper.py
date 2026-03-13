"""
D&D 2024 Wikidot Scraper
Scrapes all entries from dnd2024.wikidot.com across all major categories.
Saves results to dnd2024_data.json

Requirements:
    pip install requests beautifulsoup4
"""

import requests
from bs4 import BeautifulSoup
import json
import time

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

    links = []
    for a in content.find_all("a", href=True):
        href = str(a.get("href", ""))
        # Only include internal wiki page links
        if href.startswith("/") and ":" in href and not href.startswith("//"):
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


def scrape_entry(url):
    """Scrape the main content from a single entry page."""
    html = fetch(url)
    if not html:
        return None

    soup = BeautifulSoup(html, "html.parser")

    title = soup.find(id="page-title")
    title_text = title.get_text(strip=True) if title else "Unknown"

    content = soup.find(id="page-content")
    content_text = content.get_text(separator="\n", strip=True) if content else ""

    return {
        "title": title_text,
        "url": url,
        "content": content_text,
    }


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
            entry = scrape_entry(link["url"])
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
