"""Parser for subclass entries from dnd2024_data.json.

Parses from three sources in priority order:
1) Dedicated class subclass pages (e.g. fighter:banneret)
2) Subclass name tables in class main pages (fallback)
3) UA subclass pages (ua:subclass-*)
"""

import re
from parsers.base_parser import extract_source, extract_description
from parsers.class_parser import MAIN_CLASSES


# Sources that are considered official (non-UA) even if in the ua section.
# When a subclass from one of these sources duplicates a PHB entry,
# the richer version from this source replaces the PHB name-only entry.
OFFICIAL_SOURCES = {
    "Player's Handbook",
    "Eberron - Forge of the Artificer",
    "Forgotten Realms Subclasses UA (28.01.2025)",
    "Forgotten Realms - Heroes of Faerun",
}

# Map URL class slugs to standard class names
CLASS_SLUG_MAP = {
    "artificer": "artificer",
    "barbarian": "barbarian",
    "bard": "bard",
    "cleric": "cleric",
    "druid": "druid",
    "fighter": "fighter",
    "monk": "monk",
    "paladin": "paladin",
    "ranger": "ranger",
    "rogue": "rogue",
    "sorcerer": "sorcerer",
    "warlock": "warlock",
    "wizard": "wizard",
}

NON_SUBCLASS_SUFFIXES = {
    "main",
    "spell-list",
    "metamagic",
    "eldritch-invocation",
}

# Explicit alias map for known UA/official naming differences.
# Key/value are (class_slug, normalized_name)
ALIAS_CANONICAL = {
    ("fighter", "purple dragon knight"): ("fighter", "banneret"),
}


def _normalize_name(name: str) -> str:
    return re.sub(r"\s+", " ", name.strip().lower())


def _canonical_key(class_slug: str, name: str) -> tuple[str, str]:
    key = (class_slug, _normalize_name(name))
    return ALIAS_CANONICAL.get(key, key)


def _display_name_from_slug(slug: str) -> str:
    return slug.replace("-", " ").title()


def _parse_subclass_features(content: str) -> dict[int, list[dict]]:
    """Parse 'Level N: Feature Name' blocks from subclass content."""
    lines = content.split("\n")
    features_by_level = {}
    current_level = None
    current_name = None
    current_desc_lines = []

    def _save_current():
        if current_level is not None and current_name:
            features_by_level.setdefault(current_level, [])
            features_by_level[current_level].append(
                {
                    "name": current_name,
                    "description": " ".join(current_desc_lines).strip(),
                }
            )

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        m = re.match(r"^Level\s+(\d+)\s*:\s*(.+)", stripped)
        if m:
            _save_current()
            current_level = int(m.group(1))
            current_name = m.group(2).strip()
            current_desc_lines = []
        elif current_name is not None:
            current_desc_lines.append(stripped)

    _save_current()
    return features_by_level


def _parse_class_subclass_pages(class_subclass_data: list[dict]) -> list[dict]:
    """Parse dedicated subclass pages like fighter:banneret."""
    subclasses = []

    for entry in class_subclass_data:
        url = entry.get("url", "")
        url_part = url.rsplit("/", 1)[-1]
        if ":" not in url_part:
            continue

        class_slug, subclass_slug = url_part.split(":", 1)
        if class_slug not in CLASS_SLUG_MAP:
            continue
        if subclass_slug in NON_SUBCLASS_SUFFIXES:
            continue

        content = entry.get("content", "")
        source = extract_source(content)
        description = extract_description(content)
        features_by_level = _parse_subclass_features(content)

        title = entry.get("title", "").strip()
        if title:
            display_name = title
        else:
            display_name = _display_name_from_slug(subclass_slug)

        subclasses.append(
            {
                "name": display_name,
                "slug": subclass_slug,
                "class_slug": class_slug,
                "source": source,
                "description": description,
                "feature_levels": sorted(features_by_level.keys()),
                "features": {str(k): v for k, v in features_by_level.items()},
            }
        )

    return subclasses


def _parse_phb_subclasses(class_data: list[dict]) -> list[dict]:
    """Extract PHB subclass names from class main pages.

    These pages list subclass names in a table after '{Class} Subclasses' header,
    but don't include detailed feature descriptions.
    """
    subclasses = []

    for entry in class_data:
        url = entry.get("url", "")
        if ":main" not in url:
            continue

        class_slug = url.rsplit("/", 1)[-1].split(":")[0]
        if class_slug not in CLASS_SLUG_MAP:
            continue

        content = entry["content"]
        source = extract_source(content)
        lines = content.split("\n")

        # Find '{Class} Subclasses' section header
        class_title = class_slug.title()
        in_section = False
        for i, line in enumerate(lines):
            stripped = line.strip()

            if stripped == f"{class_title} Subclasses":
                in_section = True
                continue

            if in_section:
                # Skip the "Name" column header
                if stripped == "Name":
                    continue
                # Stop at next section (Level lines, empty, or long text >60 chars)
                if not stripped or stripped.startswith("Level ") or len(stripped) > 60:
                    break
                # Skip if next line is a long sentence (flavor text heading, not table)
                next_line = lines[i + 1].strip() if i + 1 < len(lines) else ""
                if len(next_line) > 60:
                    break
                subclasses.append(
                    {
                        "name": stripped,
                        "slug": stripped.lower().replace(" ", "-"),
                        "class_slug": class_slug,
                        "source": source,
                        "description": "",
                        "feature_levels": [],
                        "features": {},
                    }
                )

    return subclasses


def parse_subclasses(
    ua_data: list[dict],
    class_data: list[dict] | None = None,
    class_subclass_data: list[dict] | None = None,
) -> list[dict]:
    """Parse subclass entries from both PHB class pages and UA data.

    PHB subclasses (from class_data) provide names only.
    UA subclasses (from ua_data) have full feature details.
    When both exist for the same subclass, the official (PHB/Eberron) version
    is kept and the UA version is discarded.
    """
    seen: dict[tuple[str, str], dict] = {}
    seen_priority: dict[tuple[str, str], int] = {}

    # 1. Dedicated class subclass pages (official, detailed)
    if class_subclass_data:
        for sc in _parse_class_subclass_pages(class_subclass_data):
            key = _canonical_key(sc["class_slug"], sc["name"])
            seen[key] = sc
            seen_priority[key] = 3

    # 2. PHB/main page subclass names (fallback, name-only)
    if class_data:
        for sc in _parse_phb_subclasses(class_data):
            key = _canonical_key(sc["class_slug"], sc["name"])
            if key not in seen:
                seen[key] = sc
                seen_priority[key] = 1

    # 3. UA subclasses (detailed)
    for entry in ua_data:
        url = entry["url"]

        if "subclass-" not in url:
            continue

        # Parse URL: ua:subclass-{class}-{slug}
        url_part = url.rsplit("/", 1)[-1]
        remainder = url_part.replace("ua:subclass-", "")
        parts = remainder.split("-", 1)
        if len(parts) < 2:
            continue

        class_slug = parts[0]
        subclass_slug = parts[1]

        # Skip non-standard classes (psion, magic-stealer, etc.)
        if class_slug not in CLASS_SLUG_MAP:
            continue

        content = entry["content"]
        source = extract_source(content)
        description = extract_description(content)

        # Parse features by level
        features_by_level = _parse_subclass_features(content)
        feature_levels = sorted(features_by_level.keys())

        # Build display name from slug
        display_name = _display_name_from_slug(subclass_slug.rstrip("0123456789"))

        entry_data = {
            "name": display_name,
            "slug": subclass_slug,
            "class_slug": class_slug,
            "source": source,
            "description": description,
            "feature_levels": feature_levels,
            "features": {str(k): v for k, v in features_by_level.items()},
        }

        key = _canonical_key(class_slug, display_name)
        existing_prio = seen_priority.get(key, 0)

        if existing_prio >= 2:
            # Already have an official entry (detailed or promoted).
            continue

        if existing_prio == 1:
            # Replace name-only fallback if this UA source is considered official.
            if source in OFFICIAL_SOURCES:
                seen[key] = entry_data
                seen_priority[key] = 2
            continue

        # No existing entry; include UA entry.
        seen[key] = entry_data
        seen_priority[key] = 0

    return list(seen.values())
