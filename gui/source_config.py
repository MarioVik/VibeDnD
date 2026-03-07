"""Source category mappings and settings persistence for DM content filtering."""

import json
import os

from paths import settings_path

SETTINGS_PATH = settings_path()

# Map raw source book names → display category, per context
# Each context defines which categories exist and what sources map to them.

SOURCE_TO_CATEGORY = {
    "species": {
        "Player's Handbook": "Common",
        "Eberron - Forge of the Artificer": "Eberron",
        "Lorwyn - First Light": "Exotic",
        "Astarion's Book of Hungers": "Exotic",
    },
    "backgrounds": {
        "Player's Handbook": "Common",
        "Eberron - Forge of the Artificer": "Eberron",
        "Forgotten Realms - Heroes of Faerun": "Faerun",
        "Lorwyn - First Light": "Exotic",
        "Astarion's Book of Hungers": "Exotic",
    },
    "feats": {
        "Player's Handbook": "Common",
        "Forgotten Realms - Heroes of Faerun": "Faerun",
        "Eberron - Forge of the Artificer": "Exotic",
        "Lorwyn - First Light": "Exotic",
        "Astarion's Book of Hungers": "Exotic",
    },
}

# Display order for each context's categories
SECTION_ORDER = {
    "species": ["Common", "Eberron", "Exotic"],
    "backgrounds": ["Common", "Eberron", "Faerun", "Exotic"],
    "feats": ["Common", "Faerun", "Exotic"],
}


def get_category(context: str, source: str) -> str:
    """Get the display category for a source book in a given context."""
    mapping = SOURCE_TO_CATEGORY.get(context, {})
    return mapping.get(source, "Exotic")


def group_by_category(items: list[dict], context: str) -> list[tuple[str, list[dict]]]:
    """Group items by their source category, in display order.

    Returns [(category_name, [items])] with items sorted by name within each group.
    """
    order = SECTION_ORDER.get(context, [])
    groups: dict[str, list[dict]] = {cat: [] for cat in order}

    for item in items:
        cat = get_category(context, item.get("source", "Unknown"))
        if cat not in groups:
            groups[cat] = []
        groups[cat].append(item)

    # Sort items within each group
    for cat in groups:
        groups[cat].sort(key=lambda x: x.get("name", ""))

    return [(cat, groups[cat]) for cat in order if groups.get(cat)]


def default_filters() -> dict[str, dict[str, bool]]:
    """Return default filter settings (all enabled)."""
    return {
        context: {cat: True for cat in cats}
        for context, cats in SECTION_ORDER.items()
    }


def load_settings() -> dict[str, dict[str, bool]]:
    """Load source filter settings from settings.json."""
    defaults = default_filters()
    if not os.path.exists(SETTINGS_PATH):
        return defaults
    try:
        with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        filters = data.get("source_filters", {})
        # Merge with defaults to handle new categories
        for context, cats in defaults.items():
            if context not in filters:
                filters[context] = cats
            else:
                for cat, enabled in cats.items():
                    if cat not in filters[context]:
                        filters[context][cat] = enabled
        return filters
    except (json.JSONDecodeError, OSError):
        return defaults


def save_settings(filters: dict[str, dict[str, bool]]):
    """Save source filter settings to settings.json."""
    data = {}
    if os.path.exists(SETTINGS_PATH):
        try:
            with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            data = {}
    data["source_filters"] = filters
    with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
