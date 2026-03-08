"""Parser for subclass entries from UA data in dnd2024_data.json."""

import re
from parsers.base_parser import extract_source, extract_description
from parsers.class_parser import MAIN_CLASSES


# Map URL class slugs to standard class names
CLASS_SLUG_MAP = {
    "artificer": "artificer", "barbarian": "barbarian", "bard": "bard",
    "cleric": "cleric", "druid": "druid", "fighter": "fighter",
    "monk": "monk", "paladin": "paladin", "ranger": "ranger",
    "rogue": "rogue", "sorcerer": "sorcerer", "warlock": "warlock",
    "wizard": "wizard",
}


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
            features_by_level[current_level].append({
                "name": current_name,
                "description": " ".join(current_desc_lines).strip(),
            })

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        m = re.match(r'^Level\s+(\d+)\s*:\s*(.+)', stripped)
        if m:
            _save_current()
            current_level = int(m.group(1))
            current_name = m.group(2).strip()
            current_desc_lines = []
        elif current_name is not None:
            current_desc_lines.append(stripped)

    _save_current()
    return features_by_level


def parse_subclasses(ua_data: list[dict]) -> list[dict]:
    """Parse all subclass entries from UA data."""
    subclasses = []
    seen_slugs = {}  # Track by (class, base_slug) to prefer newer versions

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

        # Determine the levels where this subclass grants features
        feature_levels = sorted(features_by_level.keys())

        # Build display name from slug
        display_name = subclass_slug.rstrip("0123456789").replace("-", " ").title()

        # Track base slug (without version number) to prefer newer versions
        base_slug = re.sub(r'\d+$', '', subclass_slug)
        key = (class_slug, base_slug)

        entry_data = {
            "name": display_name,
            "slug": subclass_slug,
            "class_slug": class_slug,
            "source": source,
            "description": description,
            "feature_levels": feature_levels,
            "features": {str(k): v for k, v in features_by_level.items()},
        }

        # Prefer newer versions (e.g., arcane-archer2 over arcane-archer)
        if key in seen_slugs:
            # Replace with newer version
            seen_slugs[key] = entry_data
        else:
            seen_slugs[key] = entry_data

    subclasses = list(seen_slugs.values())
    return subclasses
