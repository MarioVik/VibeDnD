"""Mapping of generic magic items to base weapon/armor variant choices.

Generic magic items like 'Weapon, +1, +2 or +3' or 'Flame Tongue' require the
user to pick a base weapon/armor type.  This module provides the mapping and a
helper that returns the selectable options (reusing the same filter logic as
the Artificer Replicate Magic Item sub-choices).
"""

from __future__ import annotations

# ── Variant type constants ──

WEAPON = "weapon"
ARMOR = "armor"

# ── Filter constants ──

FILTER_ALL = "all"
FILTER_SWORD = "sword"
FILTER_AMMUNITION = "ammunition"
FILTER_THROWN = "thrown"
FILTER_NO_SHIELD = "no_shield"
FILTER_SHIELD_ONLY = "shield_only"

# ── Canonical lists (mirrored from level_up_logic.py) ──

_AMMO_NAMES = {"Arrows", "Bolts", "Bullets, Firearm", "Bullets, Sling", "Needles"}
_SWORD_NAMES = {"Greatsword", "Longsword", "Rapier", "Scimitar", "Shortsword"}

# ── Mapping: item name → (variant_type, filter) ──
# Only items whose base weapon/armor is NOT fixed appear here.

MAGIC_ITEM_VARIANTS: dict[str, tuple[str, str]] = {
    # Generic weapons — any weapon
    "Adamantine Weapon": (WEAPON, FILTER_ALL),
    "Dazzling Weapon": (WEAPON, FILTER_ALL),
    "Dragon Slayer": (WEAPON, FILTER_ALL),
    "Enspelled Weapon": (WEAPON, FILTER_ALL),
    "Giant Slayer": (WEAPON, FILTER_ALL),
    "Silvered Weapon": (WEAPON, FILTER_ALL),
    "Vicious Weapon": (WEAPON, FILTER_ALL),
    "Weapon of Warning": (WEAPON, FILTER_ALL),
    "Weapon, +1, +2 or +3": (WEAPON, FILTER_ALL),
    # Ammunition-only weapons
    "Ammunition of Slaying": (WEAPON, FILTER_AMMUNITION),
    "Ammunition, +1, +2, or +3": (WEAPON, FILTER_AMMUNITION),
    "Repeating Shot": (WEAPON, FILTER_AMMUNITION),
    "Walloping Ammunition": (WEAPON, FILTER_AMMUNITION),
    # Thrown-only weapons
    "Returning Weapon": (WEAPON, FILTER_THROWN),
    # Sword-only weapons
    "Dancing Sword": (WEAPON, FILTER_SWORD),
    "Defender": (WEAPON, FILTER_SWORD),
    "Flame Tongue": (WEAPON, FILTER_SWORD),
    "Frost Brand": (WEAPON, FILTER_SWORD),
    "Luck Blade": (WEAPON, FILTER_SWORD),
    "Moon-Touched Sword": (WEAPON, FILTER_SWORD),
    "Nine Lives Stealer": (WEAPON, FILTER_SWORD),
    "Sun Blade": (WEAPON, FILTER_SWORD),
    "Sword of Answering": (WEAPON, FILTER_SWORD),
    "Sword of Life Stealing": (WEAPON, FILTER_SWORD),
    "Sword of Sharpness": (WEAPON, FILTER_SWORD),
    "Sword of Vengeance": (WEAPON, FILTER_SWORD),
    "Sword of Wounding": (WEAPON, FILTER_SWORD),
    "Vorpal Sword": (WEAPON, FILTER_SWORD),
    # Generic armor — any armor except shields
    "Adamantine Armor": (ARMOR, FILTER_NO_SHIELD),
    "Armor of Gleaming": (ARMOR, FILTER_NO_SHIELD),
    "Armor of Invulnerability": (ARMOR, FILTER_NO_SHIELD),
    "Armor of Resistance": (ARMOR, FILTER_NO_SHIELD),
    "Armor of Vulnerability": (ARMOR, FILTER_NO_SHIELD),
    "Armor, +1, +2, or +3": (ARMOR, FILTER_NO_SHIELD),
    "Cast-Off Armor": (ARMOR, FILTER_NO_SHIELD),
    "Dragon Scale Mail": (ARMOR, FILTER_NO_SHIELD),
    "Enspelled Armor": (ARMOR, FILTER_NO_SHIELD),
    "Mariner's Armor": (ARMOR, FILTER_NO_SHIELD),
    "Mithral Armor": (ARMOR, FILTER_NO_SHIELD),
    "Smoldering Armor": (ARMOR, FILTER_NO_SHIELD),
}


def get_variant_info(item_name: str) -> tuple[str, str] | None:
    """Return (variant_type, filter) for a generic magic item, or None."""
    return MAGIC_ITEM_VARIANTS.get(item_name)


def get_variant_options(item_name: str, game_data) -> list[str]:
    """Return selectable base weapon/armor names for *item_name*.

    Uses the same filtering logic as ``get_sub_choice_options()`` in
    ``level_up_logic.py``.
    """
    info = get_variant_info(item_name)
    if not info or not game_data:
        return []
    vtype, vfilter = info

    if vtype == WEAPON:
        weapons = game_data.items_by_category.get("Weapons", [])
        if vfilter == FILTER_ALL:
            return sorted(
                w["name"] for w in weapons if w["name"] not in _AMMO_NAMES
            )
        if vfilter == FILTER_AMMUNITION:
            return sorted(
                w["name"]
                for w in weapons
                if w["name"] not in _AMMO_NAMES
                and "ammunition" in w.get("description", "").lower()
            )
        if vfilter == FILTER_THROWN:
            return sorted(
                w["name"]
                for w in weapons
                if w["name"] not in _AMMO_NAMES
                and "thrown" in w.get("description", "").lower()
            )
        if vfilter == FILTER_SWORD:
            return sorted(_SWORD_NAMES)
    elif vtype == ARMOR:
        armors = game_data.items_by_category.get("Armor", [])
        if vfilter == FILTER_NO_SHIELD:
            return sorted(a["name"] for a in armors if a["name"] != "Shield")
        if vfilter == FILTER_SHIELD_ONLY:
            return ["Shield"]

    return []
