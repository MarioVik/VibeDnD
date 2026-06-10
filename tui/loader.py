"""Character discovery and loading.

Primary path: VibeDnD's `paths.characters_dir()` +
`models.character_store.load_character(filepath, game_data)`, with a
single shared `gui.data_loader.GameData` instance for name resolution
(it is Tkinter-free, safe to import headless). Fallback: demo mode with
a sample character, so the TUI runs standalone too (`python -m tui
--demo`).
"""

from __future__ import annotations

import os

from .adapter import (CharacterView, FeatureView, ItemView, SpellView,
                      from_model)

_GAME_DATA = None


def _vibednd_available() -> bool:
    try:
        import models.character_store  # noqa: F401
        import paths                   # noqa: F401
        return True
    except Exception:
        return False


def game_data():
    """Shared GameData instance (loads all data JSONs once)."""
    global _GAME_DATA
    if _GAME_DATA is None:
        from gui.data_loader import GameData
        _GAME_DATA = GameData()
    return _GAME_DATA


def _character_files() -> list[str]:
    """Character save file paths from VibeDnD's characters dir."""
    import paths
    cdir = paths.characters_dir()
    if not os.path.isdir(cdir):
        return []
    return [os.path.join(cdir, entry) for entry in sorted(os.listdir(cdir))
            if entry.lower().endswith(".json")]


def _load_one(path: str) -> CharacterView | None:
    from models.character_store import load_character
    try:
        character = load_character(path, game_data())
        return from_model(character, game_data(), source_path=path)
    except Exception as exc:               # skip broken files, never fatal
        print(f"loader: skipping {os.path.basename(path)}: {exc}")
        return None


def load_characters(demo: bool = False) -> tuple[list[CharacterView], str]:
    """Return (characters, status_message)."""
    if demo:
        return [demo_character()], "demo mode"
    if not _vibednd_available():
        return [demo_character()], (
            "VibeDnD models not importable — run from the VibeDnD repo root "
            "(showing demo character)"
        )
    chars = [cv for p in _character_files() if (cv := _load_one(p))]
    if not chars:
        return [], "no saved characters found — create one in the VibeDnD GUI"
    chars.sort(key=lambda cv: cv.name.casefold())
    return chars, f"{len(chars)} character(s) loaded"


# ------------------------------------------------------------------- demo --

def demo_character() -> CharacterView:
    """Thorn Ironvale, mirroring VibeDnD's own preview sample."""
    return CharacterView(
        name="Thorn Ironvale",
        species="Half-Elf",
        background="Guide",
        class_line="Ranger 3",
        level=3,
        max_hp=28,
        current_hp=19,
        armor_class=14,
        speed="30 ft.",
        proficiency_bonus=2,
        abilities={"strength": 12, "dexterity": 16, "constitution": 14,
                   "intelligence": 10, "wisdom": 15, "charisma": 8},
        skill_profs={"Stealth", "Survival", "Perception", "Animal Handling"},
        expertise=set(),
        save_profs={"Strength", "Dexterity"},
        spells=[
            SpellView("Cure Wounds", 1, "Abjuration", "Action", "Touch",
                      description="A creature you touch regains 2d8 + your "
                      "spellcasting ability modifier hit points.",
                      prepared=True),
            SpellView("Hunter's Mark", 1, "Divination", "Bonus Action",
                      "90 feet", concentration=True,
                      description="Mark a creature; deal an extra 1d6 force "
                      "damage when you hit it with an attack roll.",
                      prepared=True),
            SpellView("Goodberry", 1, "Conjuration", "Action", "Self",
                      description="Ten berries appear in your hand. A berry "
                      "restores 1 HP and sustains a creature for one day.",
                      prepared=True),
        ],
        spell_slots={"1st": 3},
        spell_slots_used={"1st": 1},
        inventory=[
            ItemView("Longbow", "Weapons", 1, 5000,
                     "Martial ranged weapon. 1d8 piercing, range 150/600."),
            ItemView("Shortsword", "Weapons", 1, 1000,
                     "Martial melee weapon. 1d6 piercing, finesse, light."),
            ItemView("Studded Leather", "Armor", 1, 4500,
                     "Light armor. AC 12 + Dex modifier."),
            ItemView("Arrows", "Adventuring Gear", 40, 100, "A quiver's worth."),
            ItemView("Rations", "Adventuring Gear", 10, 50, "One day each."),
        ],
        wealth="35 GP",
        features=[
            FeatureView("Favored Enemy", "Ranger 1",
                        "You always have Hunter's Mark prepared and can cast "
                        "it twice without a spell slot per long rest.",
                        uses_max=2, uses_left=1),
            FeatureView("Deft Explorer", "Ranger 2",
                        "Expertise in one skill; you know two extra languages."),
            FeatureView("Hunter's Prey: Colossus Slayer", "Hunter 3",
                        "Once per turn, +1d8 damage to a creature below its "
                        "hit point maximum."),
            FeatureView("Fey Ancestry", "Species",
                        "Advantage on saves to avoid or end the Charmed "
                        "condition."),
        ],
        is_caster=True,
    )
