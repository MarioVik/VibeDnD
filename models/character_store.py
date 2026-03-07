"""Save, load, list and delete characters from the local library.

Characters are stored as JSON files in the ``characters/`` directory.
The save format uses **name references** (species name, class name, etc.)
rather than full data dicts, keeping files small and resilient to data
updates.  On load, names are resolved back to full dicts via GameData
lookups.
"""

import json
import os
import re
import uuid
from datetime import datetime

from models.character import Character
from models.ability_scores import AbilityScores

FORMAT_VERSION = 1


# ---------------------------------------------------------------------------
# Serialisation helpers
# ---------------------------------------------------------------------------

def character_to_save_dict(character: Character) -> dict:
    """Serialise a Character to a save-friendly dict using name references."""
    c = character
    return {
        "format_version": FORMAT_VERSION,
        "name": c.name,
        "species_name": c.species.get("name") if c.species else None,
        "species_sub_choice": c.species_sub_choice,
        "size_choice": c.size_choice,
        "class_name": c.character_class.get("name") if c.character_class else None,
        "background_name": c.background.get("name") if c.background else None,
        "selected_skills": list(c.selected_skills),
        "score_method": c.score_method,
        "ability_scores": dict(c.ability_scores.scores),
        "ability_bonuses": dict(c.ability_scores.bonuses),
        "ability_bonus_mode": c.ability_bonus_mode,
        "ability_bonus_assignments": dict(c.ability_bonus_assignments),
        "feat_name": c.feat.get("name") if c.feat else None,
        "species_origin_feat_name": (
            c.species_origin_feat.get("name") if c.species_origin_feat else None
        ),
        "feat_sub_choices": dict(c.feat_sub_choices),
        "selected_cantrips": list(c.selected_cantrips),
        "selected_spells": list(c.selected_spells),
        "equipment_choice_class": c.equipment_choice_class,
        "equipment_choice_background": c.equipment_choice_background,
    }


def save_dict_to_character(data: dict, game_data) -> Character:
    """Reconstruct a Character from a save dict by resolving names via
    *game_data* (a :class:`gui.data_loader.GameData` instance).
    """
    c = Character()
    c.name = data.get("name", "Unknown")

    # Resolve species
    sp_name = data.get("species_name")
    if sp_name:
        c.species = game_data.species_by_name.get(sp_name)
    c.species_sub_choice = data.get("species_sub_choice")
    c.size_choice = data.get("size_choice")

    # Resolve class
    cls_name = data.get("class_name")
    if cls_name:
        c.character_class = game_data.classes_by_name.get(cls_name)
    c.selected_skills = data.get("selected_skills", [])

    # Resolve background
    bg_name = data.get("background_name")
    if bg_name:
        c.background = game_data.backgrounds_by_name.get(bg_name)

    # Ability scores
    scores = data.get("ability_scores", {})
    bonuses = data.get("ability_bonuses", {})
    c.ability_scores = AbilityScores(scores=dict(scores), bonuses=dict(bonuses))
    c.score_method = data.get("score_method", "standard_array")
    c.ability_bonus_mode = data.get("ability_bonus_mode", "2/1")
    c.ability_bonus_assignments = data.get("ability_bonus_assignments", {})

    # Resolve feats
    feat_name = data.get("feat_name")
    if feat_name:
        c.feat = game_data.find_feat(feat_name)

    origin_feat_name = data.get("species_origin_feat_name")
    if origin_feat_name:
        c.species_origin_feat = game_data.find_feat(origin_feat_name)

    c.feat_sub_choices = data.get("feat_sub_choices", {})
    c.selected_cantrips = data.get("selected_cantrips", [])
    c.selected_spells = data.get("selected_spells", [])
    c.equipment_choice_class = data.get("equipment_choice_class", "A")
    c.equipment_choice_background = data.get("equipment_choice_background", "A")

    return c


# ---------------------------------------------------------------------------
# File helpers
# ---------------------------------------------------------------------------

def _slugify(name: str) -> str:
    """Turn a character name into a filesystem-safe slug."""
    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")
    return slug or "character"


def _make_filename(name: str) -> str:
    """Generate a unique filename from a character name."""
    slug = _slugify(name)
    short_id = uuid.uuid4().hex[:8]
    return f"{slug}_{short_id}.json"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def save_character(character: Character, characters_path: str,
                   existing_filename: str | None = None) -> str:
    """Save *character* to *characters_path*.

    If *existing_filename* is given the file is overwritten (edit mode).
    Otherwise a new file is created.  Returns the full path used.
    """
    os.makedirs(characters_path, exist_ok=True)

    if existing_filename:
        filepath = existing_filename
    else:
        filepath = os.path.join(characters_path, _make_filename(character.name))

    data = character_to_save_dict(character)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    return filepath


def load_character(filepath: str, game_data) -> Character:
    """Load a character from *filepath*, resolving names via *game_data*."""
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    return save_dict_to_character(data, game_data)


def list_saved_characters(characters_path: str) -> list[dict]:
    """Return a list of summary dicts for every saved character.

    Each dict contains: ``name``, ``species``, ``class_name``, ``path``,
    ``modified`` (ISO timestamp).  Sorted by most recently modified first.
    """
    results = []
    if not os.path.isdir(characters_path):
        return results

    for fname in os.listdir(characters_path):
        if not fname.endswith(".json"):
            continue
        fpath = os.path.join(characters_path, fname)
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
            mtime = os.path.getmtime(fpath)
            results.append({
                "name": data.get("name", "Unknown"),
                "species": data.get("species_name", "?"),
                "class_name": data.get("class_name", "?"),
                "path": fpath,
                "modified": datetime.fromtimestamp(mtime).isoformat(sep=" ", timespec="minutes"),
            })
        except (json.JSONDecodeError, OSError):
            continue

    results.sort(key=lambda r: r["modified"], reverse=True)
    return results


def delete_character(filepath: str):
    """Delete a saved character file."""
    if os.path.exists(filepath):
        os.remove(filepath)
