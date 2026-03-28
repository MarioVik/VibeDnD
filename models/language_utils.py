"""D&D 2024 language rules and helpers.

This module is GUI-free and can be imported from anywhere (wizard steps,
character viewer, PDF exporter, etc.).
"""

from __future__ import annotations

STANDARD_LANGUAGES: list[str] = [
    "Common",
    "Common Sign Language",
    "Draconic",
    "Dwarvish",
    "Elvish",
    "Giant",
    "Gnomish",
    "Goblin",
    "Halfling",
    "Orc",
]

RARE_LANGUAGES: list[str] = [
    "Abyssal",
    "Celestial",
    "Deep Speech",
    "Infernal",
    "Primordial",
    "Undercommon",
]

# Feat names that grant +3 language choices and unlock Rare Languages.
# Not currently in feats.json but wired for future use.
LINGUIST_FEAT_NAMES: set[str] = {"Linguist"}


def compute_language_sources(character) -> dict:
    """Return language grant information derived from the character's choices.

    Returns a dict with:
      "auto"           – list[str]: languages always granted (not user-chosen)
      "free_count"     – int: total number of free-choice language slots
      "can_choose_rare"– bool: True if Rare Languages are available to pick

    Only covers level-1 grants (character creation).  Ranger's Deft Explorer
    (+2 languages at level 2) is NOT included here; it is handled by the
    level-up wizard.
    """
    auto: list[str] = ["Common"]
    free_count: int = 2  # base grant for every character
    can_choose_rare: bool = False

    class_slug = ""
    if character.character_class:
        class_slug = character.character_class.get("slug", "")

    if class_slug == "druid":
        auto.append("Druidic")
    elif class_slug == "rogue":
        auto.append("Thieves' Cant")
        free_count += 1  # Rogue gets 1 extra choice on top of the base 2

    # Check background feat and species origin feat for Linguist
    for feat_obj in (character.feat, character.species_origin_feat):
        if feat_obj and feat_obj.get("name") in LINGUIST_FEAT_NAMES:
            free_count += 3
            can_choose_rare = True
            break

    return {
        "auto": auto,
        "free_count": free_count,
        "can_choose_rare": can_choose_rare,
    }


def all_languages(character) -> list[str]:
    """Return the complete, deduplicated language list for display.

    Combines auto-granted languages with the user's chosen languages.
    Order: auto languages first, then chosen languages in selection order.
    """
    sources = compute_language_sources(character)
    seen: set[str] = set()
    result: list[str] = []
    for lang in sources["auto"] + list(getattr(character, "chosen_languages", [])):
        if lang not in seen:
            seen.add(lang)
            result.append(lang)
    return result
