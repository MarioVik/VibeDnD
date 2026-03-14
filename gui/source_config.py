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
    "classes": {
        "Player's Handbook": "Common",
        "Eberron - Forge of the Artificer": "Eberron",
    },
    "subclasses": {
        "Player's Handbook": "Common",
        "Eberron - Forge of the Artificer": "Eberron",
        "Forgotten Realms - Heroes of Faerun": "Faerun",
        "Artificer UA (17.12.2024)": "Unearthed Arcana",
        "Eberron Updates UA (27.2.2025)": "Unearthed Arcana",
        "Forgotten Realms Subclasses UA (28.01.2025)": "Faerun",
        "UA4 - Horror Subclasses (06.05.2025)": "Unearthed Arcana",
        "UA6 - Arcane Subclasses (26.06.2025)": "Unearthed Arcana",
        "UA7 - Apocalyptic Subclasses (21.08.2025)": "Unearthed Arcana",
        "UA8 - Arcane Subclasses Update (18.09.2025)": "Unearthed Arcana",
        "UA10 - Subclasses Update (30.10.2025)": "Unearthed Arcana",
        "UA11 - Mystic Subclasses (15.1.2026)": "Unearthed Arcana",
        "-": "Unearthed Arcana",
    },
}

# Display order for each context's categories
SECTION_ORDER = {
    "species": ["Common", "Eberron", "Exotic"],
    "backgrounds": ["Common", "Eberron", "Faerun", "Exotic"],
    "feats": ["Common", "Faerun", "Exotic"],
    "classes": ["Common", "Eberron", "Faerun", "Unearthed Arcana"],
}

# Category name for UA playtest content
UA_CATEGORY = "Unearthed Arcana"

UA_WARNING = (
    "This option comes from Unearthed Arcana playtest material. "
    "It isn\u2019t officially finalized or guaranteed to be balanced. "
    "Make sure your DM allows playtest content before selecting it."
)


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


def confirm_ua_enable(parent) -> bool:
    """Show a confirmation dialog when enabling Unearthed Arcana content.

    Returns True if the user confirmed, False if they cancelled.
    """
    from gui.widgets import ConfirmDialog

    dlg = ConfirmDialog(parent, "Unearthed Arcana", UA_WARNING)
    return dlg.result


def handle_ua_toggle(parent, ua_var, was_enabled: bool) -> tuple[bool, bool]:
    """Handle UA checkbox transition with one-time confirmation.

    Returns (proceed, is_enabled_now).
    - proceed=False means caller should stop processing this toggle event.
    - is_enabled_now is the post-check current UA state.
    """
    is_enabled_now = bool(ua_var and ua_var.get())
    if ua_var is not None and is_enabled_now and not was_enabled:
        if not confirm_ua_enable(parent):
            ua_var.set(False)
            return False, False
    return True, is_enabled_now


def default_filters() -> dict[str, dict[str, bool]]:
    """Return default filter settings (all enabled except UA)."""
    return {
        context: {cat: (cat != UA_CATEGORY) for cat in cats}
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
                # Drop removed/unused categories so hidden stale toggles don't linger
                filters[context] = {
                    cat: filters[context].get(cat, enabled)
                    for cat, enabled in cats.items()
                }
            # UA should always start unchecked on app load.
            if UA_CATEGORY in filters[context]:
                filters[context][UA_CATEGORY] = False
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
