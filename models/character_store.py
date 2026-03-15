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
from models.class_level import ClassLevel

FORMAT_VERSION = 2


# ---------------------------------------------------------------------------
# Serialisation helpers
# ---------------------------------------------------------------------------


def character_to_save_dict(character: Character) -> dict:
    """Serialise a Character to a save-friendly dict using name references."""
    c = character
    d = {
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
        "standard_action_options": dict(c.standard_action_options),
        "equipped_weapons": list(c.equipped_weapons)
        if c.equipped_weapons is not None
        else None,
        "equipped_armor": list(c.equipped_armor)
        if c.equipped_armor is not None
        else None,
        "custom_inventory": list(c.custom_inventory),
        "removed_items": dict(c.removed_items),
        "wealth_adjust_cp": int(c.wealth_adjust_cp),
        "inventory_transactions": list(c.inventory_transactions),
    }

    # Serialize class_levels
    if c.class_levels:
        d["class_levels"] = [
            {
                "class_slug": cl.class_slug,
                "class_level": cl.class_level,
                "subclass_slug": cl.subclass_slug,
                "feat_choice": cl.feat_choice,
                "new_cantrips": list(cl.new_cantrips),
                "new_spells": list(cl.new_spells),
                "swapped_out_cantrip": cl.swapped_out_cantrip,
                "swapped_in_cantrip": cl.swapped_in_cantrip,
                "swapped_out_spell": cl.swapped_out_spell,
                "swapped_in_spell": cl.swapped_in_spell,
                "hp_roll": cl.hp_roll,
                "hit_die": cl.hit_die,
            }
            for cl in c.class_levels
        ]

    return d


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
    c.size_choice = str(data.get("size_choice") or "Medium")

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
    c.standard_action_options = data.get("standard_action_options", {})
    c.equipped_weapons = data.get("equipped_weapons")
    c.equipped_armor = data.get("equipped_armor")
    c.custom_inventory = data.get("custom_inventory", [])
    c.removed_items = data.get("removed_items", {}) or {}
    c.wealth_adjust_cp = int(data.get("wealth_adjust_cp", 0))
    c.inventory_transactions = data.get("inventory_transactions", [])

    # Load class_levels (v2) or construct from v1 data
    if "class_levels" in data:
        c.class_levels = [
            ClassLevel(
                class_slug=cl.get("class_slug", ""),
                class_level=cl.get("class_level", 1),
                subclass_slug=cl.get("subclass_slug"),
                feat_choice=cl.get("feat_choice"),
                new_cantrips=cl.get("new_cantrips", []),
                new_spells=cl.get("new_spells", []),
                swapped_out_cantrip=cl.get("swapped_out_cantrip"),
                swapped_in_cantrip=cl.get("swapped_in_cantrip"),
                swapped_out_spell=cl.get("swapped_out_spell"),
                swapped_in_spell=cl.get("swapped_in_spell"),
                hp_roll=cl.get("hp_roll"),
                hit_die=cl.get("hit_die", 0),
            )
            for cl in data["class_levels"]
        ]
    elif c.character_class:
        # v1 backward compat: create a single level 1 entry
        slug = c.character_class.get("slug", "")
        hit_die = c.character_class.get("hit_die", 8)
        c.class_levels = [ClassLevel(class_slug=slug, class_level=1, hit_die=hit_die)]

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


def save_character(
    character: Character, characters_path: str, existing_filename: str | None = None
) -> str:
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


def import_character_from_export(filepath: str, game_data) -> Character:
    """Import a character from an *exported* JSON file (produced by
    ``export_json``).  The export format differs from the save format,
    so we translate the keys before loading.

    Also handles native save-format files transparently – if the file
    already has ``format_version`` it is loaded directly.
    """
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    # If it's already in native save format, just load directly
    if "format_version" in data:
        return save_dict_to_character(data, game_data)

    # --- Translate export format → save format ---
    save = {}
    save["name"] = data.get("name", "Imported Character")
    save["species_name"] = data.get("species")
    save["species_sub_choice"] = data.get("species_sub_choice")
    save["size_choice"] = data.get("size")
    save["class_name"] = data.get("class")
    save["background_name"] = data.get("background")
    save["score_method"] = data.get("score_method", "standard_array")

    # Ability scores – extract base values from the nested dict
    abilities = data.get("abilities", {})
    scores = {}
    bonuses = {}
    for ab_name, ab_data in abilities.items():
        if isinstance(ab_data, dict):
            scores[ab_name] = ab_data.get("base", 10)
            bonuses[ab_name] = ab_data.get("bonus", 0)
        else:
            scores[ab_name] = ab_data
    save["ability_scores"] = scores
    save["ability_bonuses"] = bonuses

    # Skills
    save["selected_skills"] = data.get("skill_proficiencies", [])

    # Feats
    save["feat_name"] = data.get("background_feat")
    save["species_origin_feat_name"] = data.get("species_origin_feat")

    # Spells
    save["selected_cantrips"] = data.get("cantrips", [])
    save["selected_spells"] = data.get("spells", [])

    # Equipment
    save["equipment_choice_class"] = data.get("equipment_choice_class", "A")
    save["equipment_choice_background"] = data.get("equipment_choice_background", "A")
    save["standard_action_options"] = data.get("standard_action_options", {})
    save["equipped_weapons"] = data.get("equipped_weapons")
    save["equipped_armor"] = data.get("equipped_armor")
    save["custom_inventory"] = data.get("custom_inventory", [])
    save["wealth_adjust_cp"] = int(data.get("wealth_adjust_cp", 0))
    save["inventory_transactions"] = data.get("inventory_transactions", [])

    return save_dict_to_character(save, game_data)


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
            level = len(data.get("class_levels", [])) or 1
            results.append(
                {
                    "name": data.get("name", "Unknown"),
                    "species": data.get("species_name", "?"),
                    "class_name": data.get("class_name", "?"),
                    "level": level,
                    "path": fpath,
                    "modified": datetime.fromtimestamp(mtime).isoformat(
                        sep=" ", timespec="minutes"
                    ),
                }
            )
        except json.JSONDecodeError, OSError:
            continue

    results.sort(key=lambda r: r["modified"], reverse=True)
    return results


def delete_character(filepath: str):
    """Delete a saved character file."""
    if os.path.exists(filepath):
        os.remove(filepath)
