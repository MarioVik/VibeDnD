"""Fetch and parse item pages into data/items.json (stdlib-only).

Run:
    python parsers/fetch_items.py
"""

from __future__ import annotations

import json
import os
import re
from html import unescape
from urllib.request import Request, urlopen


BASE_URL = "http://dnd2024.wikidot.com"
ITEM_URLS = [
    ("equipment:adventuring-gear", "Adventuring Gear"),
    ("equipment:armor", "Armor"),
    ("equipment:weapon", "Weapons"),
    ("equipment:mounts-and-vehicles", "Mounts and Vehicles"),
    ("equipment:poison", "Poisons"),
    ("equipment:tool", "Tools"),
    ("magic-item:all", "Magic Items"),
]

MAGIC_TABLE_RARITIES = [
    "Common",
    "Uncommon",
    "Rare",
    "Very Rare",
    "Legendary",
    "Artifact",
    "Unknown",
]

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_FILE = os.path.join(ROOT, "data", "items.json")


def _fetch_html(url: str) -> str:
    req = Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; VibeDnD/1.0)"})
    with urlopen(req, timeout=25) as resp:
        return resp.read().decode("utf-8", errors="ignore")


def _clean_text(text: str) -> str:
    s = unescape(text).replace("\xa0", " ")
    s = re.sub(r"<[^>]+>", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _slug(s: str) -> str:
    s = s.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")


def _parse_cost_cp(cost_text: str) -> int:
    t = _clean_text(cost_text).upper().replace(",", "")
    if not t or t in {"-", "VARIES", "SPECIAL"}:
        return 0

    m = re.search(r"(\d+)\s*GP", t)
    if m:
        return int(m.group(1)) * 100
    m = re.search(r"(\d+)\s*SP", t)
    if m:
        return int(m.group(1)) * 10
    m = re.search(r"(\d+)\s*CP", t)
    if m:
        return int(m.group(1))
    m = re.search(r"\+\s*(\d+)\s*GP", t)
    if m:
        return int(m.group(1)) * 100
    return 0


def _extract_tables(html: str) -> list[str]:
    return re.findall(r"<table[^>]*>.*?</table>", html, flags=re.IGNORECASE | re.DOTALL)


def _extract_tables_with_pos(html: str) -> list[tuple[str, int]]:
    out: list[tuple[str, int]] = []
    for m in re.finditer(
        r"<table[^>]*>.*?</table>", html, flags=re.IGNORECASE | re.DOTALL
    ):
        out.append((m.group(0), m.start()))
    return out


def _extract_rows(table_html: str) -> list[str]:
    return re.findall(r"<tr[^>]*>.*?</tr>", table_html, flags=re.IGNORECASE | re.DOTALL)


def _extract_cells(row_html: str) -> list[str]:
    return re.findall(
        r"<(?:td|th)[^>]*>(.*?)</(?:td|th)>", row_html, flags=re.IGNORECASE | re.DOTALL
    )


def _first_href(cell_html: str) -> str:
    m = re.search(r'href="([^"]+)"', cell_html, flags=re.IGNORECASE)
    return m.group(1) if m else ""


def _sub_items_from_desc(text: str) -> list[str]:
    m = re.search(r"contains (?:the )?following items:\s*(.+)", text, re.IGNORECASE)
    if not m:
        return []
    payload = m.group(1).replace(" and ", ", ")
    return [p.strip(" .") for p in payload.split(",") if p.strip()]


def _strip_html_to_text(html: str) -> str:
    body = re.sub(r"<script.*?</script>", "", html, flags=re.IGNORECASE | re.DOTALL)
    body = re.sub(r"<style.*?</style>", "", body, flags=re.IGNORECASE | re.DOTALL)
    body = re.sub(
        r"</?(p|li|h1|h2|h3|h4|h5|h6|br|tr|div)>",
        "\n",
        body,
        flags=re.IGNORECASE,
    )
    text = _clean_text(body)
    text = text.replace(" \n ", "\n")
    text = re.sub(r"\n{2,}", "\n\n", text)
    return text


def _infer_magic_rarity(page_html: str, table_pos: int) -> str:
    """Infer magic-item rarity from nearby heading text before a table."""
    window_start = max(0, table_pos - 1200)
    snippet = page_html[window_start:table_pos]
    text = _clean_text(snippet)
    rarity_order = [
        "Very Rare",
        "Legendary",
        "Uncommon",
        "Artifact",
        "Common",
        "Rare",
    ]
    # Find the last rarity mention in the snippet.
    best = ("", -1)
    lower = text.lower()
    for rarity in rarity_order:
        idx = lower.rfind(rarity.lower())
        if idx > best[1]:
            best = (rarity, idx)
    return best[0] if best[1] >= 0 else ""


def parse_page(url: str, category: str) -> list[dict]:
    html = _fetch_html(url)
    page = html

    items: list[dict] = []
    if category == "Magic Items":
        tables = _extract_tables_with_pos(page)
    else:
        tables = [(t, -1) for t in _extract_tables(page)]

    for table_index, (table, table_pos) in enumerate(tables):
        rarity = ""
        if category == "Magic Items":
            if table_index < len(MAGIC_TABLE_RARITIES):
                rarity = MAGIC_TABLE_RARITIES[table_index]
            if not rarity:
                rarity = _infer_magic_rarity(page, table_pos)
        rows = _extract_rows(table)
        if len(rows) < 2:
            continue

        header_idx = -1
        headers: list[str] = []
        header_keywords = {"name", "item", "type", "property", "armor", "weapon"}
        for idx in range(min(3, len(rows))):
            probe = [_clean_text(c) for c in _extract_cells(rows[idx])]
            if len(probe) < 2:
                continue
            if header_idx < 0:
                headers = probe
                header_idx = idx
            if any(h.lower() in header_keywords for h in probe):
                headers = probe
                header_idx = idx
                break

        if len(headers) < 2:
            continue

        lower_headers = [h.lower() for h in headers]
        has_cost_column = any("cost" in h or "price" in h for h in lower_headers)
        if category != "Magic Items" and not has_cost_column:
            # Skip non-item reference tables (e.g. weapon properties/masteries).
            continue

        for row in rows[header_idx + 1 :]:
            raw_cells = _extract_cells(row)
            cells = [_clean_text(c) for c in raw_cells]
            if not cells:
                continue
            name = cells[0]
            if not name or name.lower() in {"name", "item", "armor", "tool", "type"}:
                continue

            cost_cp = 0
            desc_parts = []
            item_type = ""
            for i, header in enumerate(headers):
                if i >= len(cells):
                    continue
                value = cells[i]
                if i == 0:
                    continue
                hl = header.lower()
                if "cost" in hl or "price" in hl:
                    cost_cp = _parse_cost_cp(value)
                elif hl == "type":
                    item_type = value
                else:
                    desc_parts.append(f"{header}: {value}")

            desc = "; ".join(p for p in desc_parts if p)
            item = {
                "id": f"{_slug(category)}:{_slug(name)}",
                "name": name,
                "category": category,
                "cost_cp": int(cost_cp),
                "description": desc,
                "source": url,
            }
            if item_type:
                item["type"] = item_type
            if rarity:
                item["rarity"] = rarity
            if category == "Magic Items" and raw_cells:
                href = _first_href(raw_cells[0])
                if href.startswith("/"):
                    href = BASE_URL + href
                if "/magic-item:" in href and not href.endswith("/magic-item:all"):
                    item["detail_url"] = href
            subs = _sub_items_from_desc(desc)
            if subs:
                item["sub_items"] = subs
            items.append(item)
    return items


def enrich_magic_item_descriptions(items: list[dict]):
    cache: dict[str, str] = {}
    for item in items:
        if item.get("category") != "Magic Items":
            continue
        detail_url = item.get("detail_url")
        if not detail_url:
            continue
        if detail_url not in cache:
            try:
                html = _fetch_html(detail_url)
            except Exception:
                cache[detail_url] = ""
                continue
            m = re.search(
                r'<div id="page-content"[^>]*>(.*?)<div id="page-info-break"',
                html,
                flags=re.IGNORECASE | re.DOTALL,
            )
            content_html = m.group(1) if m else html
            cache[detail_url] = _strip_html_to_text(content_html)
        full = cache.get(detail_url, "")
        if full:
            item["full_description"] = full


def main():
    all_items = []
    seen = set()

    for path, category in ITEM_URLS:
        url = f"{BASE_URL}/{path}"
        print(f"Parsing {url}")
        for item in parse_page(url, category):
            if item["id"] in seen:
                continue
            seen.add(item["id"])
            all_items.append(item)

    enrich_magic_item_descriptions(all_items)

    os.makedirs(os.path.dirname(OUT_FILE), exist_ok=True)
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_items, f, indent=2, ensure_ascii=False)

    print(f"Saved {len(all_items)} items -> {OUT_FILE}")


if __name__ == "__main__":
    main()
