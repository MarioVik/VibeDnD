"""Helpers for level-1 spell grants during character creation.

This module keeps base class spell selections separate from extraordinary
spell access granted by species, feats/backgrounds, and class features.
"""

from __future__ import annotations

import re

_SPELLCASTING_ABILITIES = ("Intelligence", "Wisdom", "Charisma")

_CLASS_AUTO_GRANTS = {
    "artificer": {
        "source_id": "class:artificer:tinkers_magic",
        "source_label": "Tinker's Magic",
        "granted_entries": [
            {"spell_name": "Mending", "kind": "cantrip"},
        ],
    },
    "druid": {
        "source_id": "class:druid:druidic",
        "source_label": "Druidic",
        "granted_entries": [
            {
                "spell_name": "Speak with Animals",
                "kind": "spell",
                "detail_note": "When you cast this spell as a ritual, its duration is 8 hours.",
            },
        ],
    },
    "ranger": {
        "source_id": "class:ranger:favored_enemy",
        "source_label": "Favored Enemy",
        "granted_entries": [
            {"spell_name": "Hunter's Mark", "kind": "spell"},
        ],
    },
}

_WARLOCK_INVOCATION_GRANTS = {
    "Armor of Shadows": [
        {
            "spell_name": "Mage Armor",
            "kind": "spell",
            "free_cast": "At Will",
            "detail_note": "You can cast this spell only on yourself with this invocation.",
        }
    ],
    "Fiendish Vigor": [
        {
            "spell_name": "False Life",
            "kind": "spell",
            "free_cast": "At Will",
            "detail_note": (
                "When you cast this spell with Fiendish Vigor, you gain the maximum "
                "number of Temporary Hit Points instead of rolling."
            ),
        }
    ],
    "Mask of Many Faces": [
        {
            "spell_name": "Disguise Self",
            "kind": "spell",
            "free_cast": "At Will",
        }
    ],
    "Pact of the Chain": [
        {
            "spell_name": "Find Familiar",
            "kind": "spell",
            "free_cast": "At Will",
        }
    ],
}

_ELF_LINEAGE_CANTRIPS = {
    "Drow": "Dancing Lights",
    "High Elf": "Prestidigitation",
    "Wood Elf": "Druidcraft",
    "Lorwyn Elf": "Thorn Whip",
    "Shadowmoor Elf": "Starry Wisp",
}

_ELF_LINEAGE_SPELLS: dict[str, dict[int, str]] = {
    "Drow": {3: "Faerie Fire", 5: "Darkness"},
    "High Elf": {3: "Detect Magic", 5: "Misty Step"},
    "Wood Elf": {3: "Longstrider", 5: "Pass Without Trace"},
    "Lorwyn Elf": {3: "Command", 5: "Silence"},
    "Shadowmoor Elf": {3: "Heroism", 5: "Gentle Repose"},
}

_TIEFLING_LEGACY_CANTRIPS = {
    "Abyssal": "Poison Spray",
    "Chthonic": "Chill Touch",
    "Infernal": "Fire Bolt",
}

_TIEFLING_LEGACY_SPELLS: dict[str, dict[int, str]] = {
    "Abyssal": {3: "Ray Of Sickness", 5: "Hold Person"},
    "Chthonic": {3: "False Life", 5: "Ray Of Enfeeblement"},
    "Infernal": {3: "Hellish Rebuke", 5: "Darkness"},
}

_MARK_FEAT_DATA = {
    "Mark Of Detection": {
        "ability_choice_required": True,
        "granted_entries": [
            {
                "spell_name": "Detect Magic",
                "kind": "spell",
                "free_cast": "1 / Long Rest",
            },
            {
                "spell_name": "Detect Poison and Disease",
                "kind": "spell",
                "free_cast": "1 / Long Rest",
            },
        ],
        "expansion_spells": ["Detect Evil and Good", "Identify"],
    },
    "Mark Of Finding": {
        "ability_choice_required": True,
        "granted_entries": [
            {
                "spell_name": "Hunter's Mark",
                "kind": "spell",
                "free_cast": "1 / Long Rest",
            }
        ],
        "expansion_spells": ["Faerie Fire", "Longstrider"],
    },
    "Mark Of Handling": {
        "ability_choice_required": True,
        "granted_entries": [
            {
                "spell_name": "Animal Friendship",
                "kind": "spell",
                "free_cast": "1 / Long Rest",
            },
            {
                "spell_name": "Speak with Animals",
                "kind": "spell",
                "free_cast": "1 / Long Rest",
            },
        ],
        "expansion_spells": ["Command", "Find Familiar"],
    },
    "Mark Of Healing": {
        "ability_choice_required": True,
        "granted_entries": [
            {
                "spell_name": "Cure Wounds",
                "kind": "spell",
                "free_cast": "1 / Long Rest",
            }
        ],
        "expansion_spells": ["False Life", "Healing Word"],
    },
    "Mark Of Hospitality": {
        "ability_choice_required": True,
        "granted_entries": [
            {
                "spell_name": "Purify Food and Drink",
                "kind": "spell",
                "free_cast": "1 / Long Rest",
            },
            {
                "spell_name": "Unseen Servant",
                "kind": "spell",
                "free_cast": "1 / Long Rest",
            },
        ],
        "expansion_spells": ["Goodberry", "Sleep"],
    },
    "Mark Of Making": {
        "ability_choice_required": True,
        "granted_entries": [
            {"spell_name": "Mending", "kind": "cantrip"},
            {
                "spell_name": "Magic Weapon",
                "kind": "spell",
                "free_cast": "1 / Long Rest",
            },
        ],
        "expansion_spells": ["Identify", "Tenser's Floating Disk"],
    },
    "Mark Of Passage": {
        "ability_choice_required": True,
        "granted_entries": [
            {
                "spell_name": "Misty Step",
                "kind": "spell",
                "free_cast": "1 / Long Rest",
            }
        ],
        "expansion_spells": ["Expeditious Retreat", "Jump"],
    },
    "Mark Of Scribing": {
        "ability_choice_required": True,
        "granted_entries": [
            {"spell_name": "Message", "kind": "cantrip"},
            {
                "spell_name": "Comprehend Languages",
                "kind": "spell",
                "free_cast": "1 / Long Rest",
            },
        ],
        "expansion_spells": ["Command", "Illusory Script"],
    },
    "Mark Of Sentinel": {
        "ability_choice_required": True,
        "granted_entries": [
            {
                "spell_name": "Shield",
                "kind": "spell",
                "free_cast": "1 / Long Rest",
            }
        ],
        "expansion_spells": ["Compelled Duel", "Shield of Faith"],
    },
    "Mark Of Shadow": {
        "ability_choice_required": True,
        "granted_entries": [
            {"spell_name": "Minor Illusion", "kind": "cantrip"},
            {
                "spell_name": "Invisibility",
                "kind": "spell",
                "free_cast": "1 / Long Rest",
            },
        ],
        "expansion_spells": ["Disguise Self", "Silent Image"],
    },
    "Mark Of Storm": {
        "ability_choice_required": True,
        "granted_entries": [
            {"spell_name": "Thunderclap", "kind": "cantrip"},
        ],
        "expansion_spells": ["Feather Fall", "Fog Cloud"],
    },
    "Mark Of Warding": {
        "ability_choice_required": True,
        "granted_entries": [
            {
                "spell_name": "Alarm",
                "kind": "spell",
                "free_cast": "1 / Long Rest",
            },
            {
                "spell_name": "Mage Armor",
                "kind": "spell",
                "free_cast": "1 / Long Rest",
            },
        ],
        "expansion_spells": ["Armor of Agathys", "Sanctuary"],
    },
}


def _norm(value) -> str:
    return str(value or "").strip().casefold()


def _slugify(value) -> str:
    return re.sub(r"[^a-z0-9]+", "_", _norm(value)).strip("_")


def _choice_store(character, *, create: bool = True) -> dict:
    store = getattr(character, "spell_grant_choices", None)
    if isinstance(store, dict):
        return store
    if not create:
        return {}
    store = {}
    character.spell_grant_choices = store
    return store


def _source_choice(character, source_id: str, *, create: bool = False) -> dict:
    store = _choice_store(character, create=create)
    raw = store.get(source_id)
    if isinstance(raw, dict):
        return raw
    if not create:
        return {}
    raw = {}
    store[source_id] = raw
    return raw


def get_spell_grant_choice_value(character, source_id: str, key: str, default=None):
    return _source_choice(character, source_id, create=False).get(key, default)


def set_spell_grant_choice_value(character, source_id: str, key: str, value):
    bucket = _source_choice(character, source_id, create=True)
    if value in (None, "", []):
        bucket.pop(key, None)
    else:
        bucket[key] = value
    if not bucket:
        _choice_store(character).pop(source_id, None)


def _spell_index(game_data) -> dict[str, dict]:
    index = getattr(game_data, "_spell_name_index", None)
    if isinstance(index, dict):
        return index
    index = {
        str(spell.get("name", "")).strip(): spell
        for spell in getattr(game_data, "spells", [])
        if str(spell.get("name", "")).strip()
    }
    setattr(game_data, "_spell_name_index", index)
    return index


def _find_spell(game_data, spell_name: str) -> dict | None:
    return _spell_index(game_data).get(str(spell_name or "").strip())


def _spell_sort_key(game_data, spell_name: str) -> tuple[int, str]:
    spell = _find_spell(game_data, spell_name) or {}
    return (int(spell.get("level", 99) or 99), str(spell_name or "").casefold())


def _sort_spell_names(game_data, spell_names) -> list[str]:
    unique = []
    seen = set()
    for spell_name in spell_names:
        clean = str(spell_name or "").strip()
        if clean and clean not in seen:
            unique.append(clean)
            seen.add(clean)
    return sorted(unique, key=lambda name: _spell_sort_key(game_data, name))


def _copy_entry(entry: dict, source_id: str, source_label: str) -> dict:
    copied = dict(entry)
    copied["source_id"] = source_id
    copied["source_label"] = source_label
    return copied


def _spell_entry(
    source_id: str,
    source_label: str,
    spell_name: str,
    kind: str,
    *,
    free_cast: str | None = None,
    ritual_only: bool = False,
    dragonmark_eligible: bool = False,
    detail_note: str = "",
):
    return {
        "source_id": source_id,
        "source_label": source_label,
        "spell_name": spell_name,
        "kind": kind,
        "free_cast": free_cast,
        "ritual_only": ritual_only,
        "dragonmark_eligible": dragonmark_eligible,
        "detail_note": detail_note,
    }


def _base_source(source_id: str, source_label: str) -> dict:
    return {
        "source_id": source_id,
        "source_label": source_label,
        "ability_choice_required": False,
        "ability_value": "",
        "ability_options": [],
        "source_list_options": [],
        "source_list_value": "",
        "cantrip_choice_count": 0,
        "spell_choice_count": 0,
        "selected_cantrips": [],
        "selected_spells": [],
        "cantrip_options": [],
        "spell_options": [],
        "granted_entries": [],
        "expansion_spells": [],
        "resource_entries": [],
    }


def _grant_from_config(source_id: str, source_label: str, config: dict) -> dict:
    source = _base_source(source_id, source_label)
    source["ability_choice_required"] = bool(config.get("ability_choice_required"))
    source["ability_options"] = list(config.get("ability_options", _SPELLCASTING_ABILITIES))
    source["granted_entries"] = [
        _copy_entry(entry, source_id, source_label)
        for entry in config.get("granted_entries", [])
    ]
    source["expansion_spells"] = list(config.get("expansion_spells", []))
    return source


def _active_feat_sources(character, game_data) -> list[dict]:
    sources: list[dict] = []

    background = getattr(character, "background", None) or {}
    raw_background_feat = str(background.get("feat", "") or "").strip()
    if raw_background_feat:
        feat = game_data.find_feat(raw_background_feat)
        if feat:
            sources.append(
                {
                    "slot": "background",
                    "raw_name": raw_background_feat,
                    "feat_name": feat.get("name", raw_background_feat),
                    "source_id": f"background_feat:{_slugify(raw_background_feat)}",
                    "source_label": raw_background_feat,
                    "feat": feat,
                }
            )

    species_feat = getattr(character, "species_origin_feat", None) or {}
    species_feat_name = str(species_feat.get("name", "") or "").strip()
    if species_feat_name:
        sources.append(
            {
                "slot": "species",
                "raw_name": species_feat_name,
                "feat_name": species_feat_name,
                "source_id": f"species_feat:{_slugify(species_feat_name)}",
                "source_label": species_feat_name,
                "feat": species_feat,
            }
        )

    lessons_feat_name = str(
        (getattr(character, "level1_class_choices", {}) or {}).get("warlock_lessons_feat", "") or ""
    ).strip()
    if lessons_feat_name:
        feat = game_data.find_feat(lessons_feat_name)
        if feat:
            sources.append(
                {
                    "slot": "lessons",
                    "raw_name": lessons_feat_name,
                    "feat_name": feat.get("name", lessons_feat_name),
                    "source_id": f"warlock_lessons_feat:{_slugify(lessons_feat_name)}",
                    "source_label": lessons_feat_name,
                    "feat": feat,
                }
            )

    return sources


def _active_mark_feat_names(character, game_data) -> list[tuple[str, str, str]]:
    names: list[tuple[str, str, str]] = []
    for feat_source in _active_feat_sources(character, game_data):
        feat_name = str(feat_source["feat_name"])
        if feat_name in _MARK_FEAT_DATA:
            names.append(
                (feat_source["source_id"], feat_source["source_label"], feat_name)
            )
    return names


def _has_potent_dragonmark(character, game_data) -> bool:
    for feat_source in _active_feat_sources(character, game_data):
        if _norm(feat_source["feat_name"]) == "potent dragonmark":
            return True
    return False


def _build_species_sources(character, game_data) -> list[dict]:
    species = getattr(character, "species", None) or {}
    species_name = str(species.get("name", "") or "").strip()
    sub_choice = str(getattr(character, "species_sub_choice", "") or "").strip()
    if not species_name:
        return []

    sources: list[dict] = []

    if species_name == "Aasimar":
        source = _base_source("species:aasimar", "Aasimar")
        source["ability_value"] = "Charisma"
        source["granted_entries"] = [
            _spell_entry(source["source_id"], source["source_label"], "Light", "cantrip")
        ]
        sources.append(source)

    if species_name == "Elf" and sub_choice in _ELF_LINEAGE_CANTRIPS:
        source = _base_source(f"species:elf:{_slugify(sub_choice)}", sub_choice)
        source["ability_choice_required"] = True
        source["ability_options"] = list(_SPELLCASTING_ABILITIES)
        granted = [
            _spell_entry(
                source["source_id"],
                source["source_label"],
                _ELF_LINEAGE_CANTRIPS[sub_choice],
                "cantrip",
            )
        ]
        lineage_spells = _ELF_LINEAGE_SPELLS.get(sub_choice, {})
        for min_level in sorted(lineage_spells):
            if character.level >= min_level:
                granted.append(
                    _spell_entry(
                        source["source_id"],
                        source["source_label"],
                        lineage_spells[min_level],
                        "spell",
                        free_cast="1 / Long Rest",
                    )
                )
        source["granted_entries"] = granted
        sources.append(source)

    if species_name == "Gnome" and sub_choice == "Forest Gnome":
        source = _base_source("species:gnome:forest", "Forest Gnome")
        source["ability_choice_required"] = True
        source["ability_options"] = list(_SPELLCASTING_ABILITIES)
        source["granted_entries"] = [
            _spell_entry(source["source_id"], source["source_label"], "Minor Illusion", "cantrip"),
            _spell_entry(
                source["source_id"],
                source["source_label"],
                "Speak with Animals",
                "spell",
                free_cast="PB / Long Rest",
            ),
        ]
        sources.append(source)

    if species_name == "Gnome" and sub_choice == "Rock Gnome":
        source = _base_source("species:gnome:rock", "Rock Gnome")
        source["ability_choice_required"] = True
        source["ability_options"] = list(_SPELLCASTING_ABILITIES)
        source["granted_entries"] = [
            _spell_entry(source["source_id"], source["source_label"], "Mending", "cantrip"),
            _spell_entry(
                source["source_id"],
                source["source_label"],
                "Prestidigitation",
                "cantrip",
            ),
        ]
        sources.append(source)

    if species_name == "Tiefling" and sub_choice in _TIEFLING_LEGACY_CANTRIPS:
        source = _base_source(f"species:tiefling:{_slugify(sub_choice)}", sub_choice)
        source["ability_choice_required"] = True
        source["ability_options"] = list(_SPELLCASTING_ABILITIES)
        granted = [
            _spell_entry(source["source_id"], source["source_label"], "Thaumaturgy", "cantrip"),
            _spell_entry(
                source["source_id"],
                source["source_label"],
                _TIEFLING_LEGACY_CANTRIPS[sub_choice],
                "cantrip",
            ),
        ]
        legacy_spells = _TIEFLING_LEGACY_SPELLS.get(sub_choice, {})
        for min_level in sorted(legacy_spells):
            if character.level >= min_level:
                granted.append(
                    _spell_entry(
                        source["source_id"],
                        source["source_label"],
                        legacy_spells[min_level],
                        "spell",
                        free_cast="1 / Long Rest",
                    )
                )
        source["granted_entries"] = granted
        sources.append(source)

    if species_name == "Khoravar":
        source = _base_source("species:khoravar", "Khoravar")
        source["ability_choice_required"] = True
        source["ability_options"] = list(_SPELLCASTING_ABILITIES)
        source["granted_entries"] = [
            _spell_entry(source["source_id"], source["source_label"], "Friends", "cantrip")
        ]
        sources.append(source)

    if species_name == "Faerie":
        source = _base_source("species:faerie", "Faerie")
        source["ability_choice_required"] = True
        source["ability_options"] = list(_SPELLCASTING_ABILITIES)
        source["granted_entries"] = [
            _spell_entry(source["source_id"], source["source_label"], "Druidcraft", "cantrip")
        ]
        sources.append(source)

    if species_name == "Flamekin":
        source = _base_source("species:flamekin", "Flamekin")
        source["ability_choice_required"] = True
        source["ability_options"] = list(_SPELLCASTING_ABILITIES)
        source["granted_entries"] = [
            _spell_entry(source["source_id"], source["source_label"], "Produce Flame", "cantrip")
        ]
        sources.append(source)

    if species_name == "Rimekin":
        source = _base_source("species:rimekin", "Rimekin")
        source["ability_choice_required"] = True
        source["ability_options"] = list(_SPELLCASTING_ABILITIES)
        source["granted_entries"] = [
            _spell_entry(source["source_id"], source["source_label"], "Ray of Frost", "cantrip")
        ]
        sources.append(source)

    if species_name == "Deep Gnome" and character.level >= 3:
        source = _base_source(
            "species:deep_gnome:svirfneblin_magic",
            "Gift of the Svirfneblin",
        )
        source["ability_choice_required"] = True
        source["ability_options"] = list(_SPELLCASTING_ABILITIES)
        granted = [
            _spell_entry(
                source["source_id"],
                source["source_label"],
                "Disguise Self",
                "spell",
                free_cast="1 / Long Rest",
            )
        ]
        if character.level >= 5:
            granted.append(
                _spell_entry(
                    source["source_id"],
                    source["source_label"],
                    "Nondetection",
                    "spell",
                    free_cast="1 / Long Rest",
                    detail_note=(
                        "When you cast Nondetection with this trait, no material component is required."
                    ),
                )
            )
        source["granted_entries"] = granted
        sources.append(source)

    return sources


def _magic_initiate_sources(raw_name: str, source_id: str, source_label: str, character, game_data) -> dict:
    source = _base_source(source_id, source_label)
    source["ability_choice_required"] = True
    source["ability_options"] = list(_SPELLCASTING_ABILITIES)

    match = re.search(r"\(([^)]+)\)", raw_name)
    fixed_list = match.group(1).strip() if match else ""
    list_value = fixed_list or str(get_spell_grant_choice_value(character, source_id, "source_list", "") or "").strip()
    source["source_list_options"] = [] if fixed_list else ["Cleric", "Druid", "Wizard"]
    source["source_list_value"] = list_value

    if not list_value:
        return source

    cantrip_options = [
        spell["name"]
        for spell in getattr(game_data, "cantrips_for_class", lambda _name: [])(list_value)
    ]
    spell_options = [
        spell["name"]
        for spell in getattr(game_data, "spells_for_class", lambda _name, max_level=1: [])(list_value, max_level=1)
        if int(spell.get("level", 0) or 0) == 1
    ]
    source["cantrip_choice_count"] = 2
    source["spell_choice_count"] = 1
    source["cantrip_options"] = _sort_spell_names(game_data, cantrip_options)
    source["spell_options"] = _sort_spell_names(game_data, spell_options)

    selected_cantrips = _sort_spell_names(
        game_data,
        get_spell_grant_choice_value(character, source_id, "cantrips", []) or [],
    )[:2]
    selected_spells = _sort_spell_names(
        game_data,
        get_spell_grant_choice_value(character, source_id, "spells", []) or [],
    )[:1]
    source["selected_cantrips"] = selected_cantrips
    source["selected_spells"] = selected_spells

    for spell_name in selected_cantrips:
        source["granted_entries"].append(
            _spell_entry(source_id, source_label, spell_name, "cantrip")
        )
    for spell_name in selected_spells:
        source["granted_entries"].append(
            _spell_entry(
                source_id,
                source_label,
                spell_name,
                "spell",
                free_cast="1 / Long Rest",
            )
        )

    return source


def _single_spell_choice_source(
    source_id: str,
    source_label: str,
    character,
    game_data,
    *,
    ability_choice_required: bool,
    ability_value: str = "",
    spell_options: list[str],
    free_cast: str | None = None,
    cantrip_options: list[str] | None = None,
    spell_detail_note: str = "",
):
    source = _base_source(source_id, source_label)
    source["ability_choice_required"] = ability_choice_required
    source["ability_options"] = list(_SPELLCASTING_ABILITIES)
    source["ability_value"] = ability_value
    if cantrip_options:
        source["cantrip_choice_count"] = 1
        source["cantrip_options"] = _sort_spell_names(game_data, cantrip_options)
        selected_cantrips = _sort_spell_names(
            game_data,
            get_spell_grant_choice_value(character, source_id, "cantrips", []) or [],
        )[:1]
        source["selected_cantrips"] = selected_cantrips
        for spell_name in selected_cantrips:
            source["granted_entries"].append(
                _spell_entry(source_id, source_label, spell_name, "cantrip")
            )

    source["spell_choice_count"] = 1
    source["spell_options"] = _sort_spell_names(game_data, spell_options)
    selected_spells = _sort_spell_names(
        game_data,
        get_spell_grant_choice_value(character, source_id, "spells", []) or [],
    )[:1]
    source["selected_spells"] = selected_spells
    for spell_name in selected_spells:
        source["granted_entries"].append(
            _spell_entry(
                source_id,
                source_label,
                spell_name,
                "spell",
                free_cast=free_cast,
                detail_note=spell_detail_note,
            )
        )
    return source


def _fixed_feat_source(source_id: str, source_label: str, *, cantrips=None, spells=None, ability_choice_required=False):
    source = _base_source(source_id, source_label)
    source["ability_choice_required"] = ability_choice_required
    source["ability_options"] = list(_SPELLCASTING_ABILITIES)
    for entry in cantrips or []:
        source["granted_entries"].append(
            _spell_entry(
                source_id,
                source_label,
                entry["spell_name"],
                "cantrip",
                detail_note=entry.get("detail_note", ""),
            )
        )
    for entry in spells or []:
        source["granted_entries"].append(
            _spell_entry(
                source_id,
                source_label,
                entry["spell_name"],
                "spell",
                free_cast=entry.get("free_cast"),
                ritual_only=bool(entry.get("ritual_only")),
                detail_note=entry.get("detail_note", ""),
            )
        )
    return source


def _build_feat_source(feat_source: dict, character, game_data) -> dict | None:
    raw_name = str(feat_source["raw_name"])
    feat_name = str(feat_source["feat_name"])
    source_id = feat_source["source_id"]
    source_label = feat_source["source_label"]

    if _norm(feat_name) == "magic initiate":
        return _magic_initiate_sources(raw_name, source_id, source_label, character, game_data)

    if feat_name == "Aberrant Dragonmark":
        return _single_spell_choice_source(
            source_id,
            source_label,
            character,
            game_data,
            ability_choice_required=False,
            ability_value="Constitution",
            cantrip_options=[
                spell["name"]
                for spell in getattr(game_data, "cantrips_for_class", lambda _name: [])("Sorcerer")
            ],
            spell_options=[
                spell["name"]
                for spell in getattr(game_data, "spells_for_class", lambda _name, max_level=1: [])("Sorcerer", max_level=1)
                if int(spell.get("level", 0) or 0) == 1
            ],
            free_cast="1 / Short or Long Rest",
        )

    if feat_name == "Genie Magic":
        return _single_spell_choice_source(
            source_id,
            source_label,
            character,
            game_data,
            ability_choice_required=True,
            spell_options=[
                spell["name"]
                for spell in getattr(game_data, "spells_for_class", lambda _name, max_level=1: [])("Sorcerer", max_level=1)
                if int(spell.get("level", 0) or 0) == 1
                and str(spell.get("casting_time", "") or "").strip().casefold() == "action"
            ],
            free_cast="1 / Long Rest",
        )

    if feat_name == "Vampire Touched":
        source = _single_spell_choice_source(
            source_id,
            source_label,
            character,
            game_data,
            ability_choice_required=True,
            spell_options=[
                spell["name"]
                for spell in getattr(game_data, "spells", [])
                if int(spell.get("level", 0) or 0) == 1
                and str(spell.get("school", "") or "").strip() in {"Enchantment", "Illusion"}
            ],
            free_cast="1 / Long Rest",
        )
        source["granted_entries"].append(
            _spell_entry(
                source_id,
                source_label,
                "Spider Climb",
                "spell",
                free_cast="1 / Long Rest",
                detail_note="When cast with this feat, you must target yourself.",
            )
        )
        return source

    if feat_name == "Boon Of Siberys":
        siberys_choices = [
            "Animal Shapes",
            "Control Weather",
            "Demiplane",
            "Heroes' Feast",
            "Maze",
            "Mind Blank",
            "Plane Shift",
            "Project Image",
            "Regenerate",
            "Symbol",
            "Teleport",
            "True Seeing",
        ]
        return _single_spell_choice_source(
            source_id,
            source_label,
            character,
            game_data,
            ability_choice_required=True,
            spell_options=[
                spell["name"]
                for spell in getattr(game_data, "spells", [])
                if "Sorcerer" in spell.get("classes", []) or spell.get("name") in siberys_choices
            ],
            free_cast="1 / Short or Long Rest",
        )

    if feat_name == "Cold Caster":
        return _fixed_feat_source(
            source_id,
            source_label,
            cantrips=[{"spell_name": "Ray of Frost"}],
            ability_choice_required=True,
        )

    if feat_name == "Light Bringer":
        return _fixed_feat_source(
            source_id,
            source_label,
            cantrips=[{"spell_name": "Light"}],
            ability_choice_required=True,
        )

    fixed_feat_sources = {
        "Emerald Enclave Fledgling": _fixed_feat_source(
            source_id,
            source_label,
            spells=[
                {
                    "spell_name": "Speak with Animals",
                    "detail_note": "When you cast this spell as a ritual, its duration is 8 hours.",
                }
            ],
            ability_choice_required=True,
        ),
        "Spellfire Spark": _fixed_feat_source(
            source_id,
            source_label,
            cantrips=[
                {
                    "spell_name": "Sacred Flame",
                    "detail_note": "You can also cast this cantrip as a Bonus Action a number of times equal to your Proficiency Bonus per Long Rest.",
                }
            ],
            ability_choice_required=True,
        ),
        "Child Of The Sun": _fixed_feat_source(
            source_id,
            source_label,
            spells=[{"spell_name": "Faerie Fire", "free_cast": "1 / Long Rest"}],
            ability_choice_required=True,
        ),
        "Shadowmoor Hexer": _fixed_feat_source(
            source_id,
            source_label,
            spells=[{"spell_name": "Hex", "free_cast": "1 / Long Rest"}],
            ability_choice_required=True,
        ),
        "Enclave Magic": _fixed_feat_source(
            source_id,
            source_label,
            spells=[
                {
                    "spell_name": "Beast Sense",
                    "free_cast": "1 / Long Rest",
                    "detail_note": "When you cast this spell with this feat, it doesn't require Concentration.",
                }
            ],
            ability_choice_required=True,
        ),
        "Cloying Mists": _fixed_feat_source(
            source_id,
            source_label,
            spells=[{"spell_name": "Fog Cloud", "free_cast": "1 / Long Rest"}],
            ability_choice_required=True,
        ),
        "Treacherous Allure": _fixed_feat_source(
            source_id,
            source_label,
            spells=[{"spell_name": "Charm Person", "free_cast": "1 / Long Rest"}],
            ability_choice_required=True,
        ),
        "Boon Of Revelry": _fixed_feat_source(
            source_id,
            source_label,
            spells=[
                {
                    "spell_name": "Otto's Irresistible Dance",
                    "free_cast": "1 / Long Rest",
                }
            ],
        ),
        "Boon Of Misty Escape": _fixed_feat_source(
            source_id,
            source_label,
            spells=[
                {
                    "spell_name": "Gaseous Form",
                    "free_cast": "1 / Long Rest",
                    "detail_note": (
                        "You cast this spell only when you drop to 0 Hit Points but aren't killed outright."
                    ),
                }
            ],
            ability_choice_required=True,
        ),
    }
    if feat_name in fixed_feat_sources:
        return fixed_feat_sources[feat_name]

    if feat_name in _MARK_FEAT_DATA:
        config = _MARK_FEAT_DATA[feat_name]
        return _grant_from_config(source_id, source_label, config)

    return None


def _build_class_sources(character, game_data) -> list[dict]:
    cls = getattr(character, "character_class", None) or {}
    slug = str(cls.get("slug", "") or "").strip()
    if not slug:
        return []

    sources: list[dict] = []
    auto_config = _CLASS_AUTO_GRANTS.get(slug)
    if auto_config:
        source = _base_source(auto_config["source_id"], auto_config["source_label"])
        source["granted_entries"] = [
            _copy_entry(entry, source["source_id"], source["source_label"])
            for entry in auto_config["granted_entries"]
        ]
        if slug in {"artificer", "druid", "ranger"}:
            source["ability_value"] = str(cls.get("spellcasting_ability", "") or "")
        sources.append(source)

    if slug == "warlock":
        invocation = str(
            (getattr(character, "level1_class_choices", {}) or {}).get("warlock_invocation", "") or ""
        ).strip()
        if invocation in _WARLOCK_INVOCATION_GRANTS:
            source_id = f"class:warlock:invocation:{_slugify(invocation)}"
            source = _base_source(source_id, invocation)
            source["ability_value"] = str(cls.get("spellcasting_ability", "") or "")
            source["granted_entries"] = [
                _copy_entry(entry, source_id, invocation)
                for entry in _WARLOCK_INVOCATION_GRANTS[invocation]
            ]
            sources.append(source)

        if invocation == "Pact of the Tome":
            source = _base_source("class:warlock:invocation:pact_of_the_tome", "Pact of the Tome")
            source["ability_value"] = str(cls.get("spellcasting_ability", "") or "")
            choices = getattr(character, "level1_class_choices", {}) or {}
            for spell_name in choices.get("warlock_tome_cantrips", []) or []:
                clean = str(spell_name or "").strip()
                if clean:
                    source["granted_entries"].append(
                        _spell_entry(source["source_id"], source["source_label"], clean, "cantrip")
                    )
            for spell_name in choices.get("warlock_tome_rituals", []) or []:
                clean = str(spell_name or "").strip()
                if clean:
                    source["granted_entries"].append(
                        _spell_entry(
                            source["source_id"],
                            source["source_label"],
                            clean,
                            "spell",
                            ritual_only=True,
                        )
                    )
            sources.append(source)

    return sources


def _build_active_sources_raw(character, game_data) -> list[dict]:
    sources: list[dict] = []
    sources.extend(_build_class_sources(character, game_data))
    sources.extend(_build_species_sources(character, game_data))
    for feat_source in _active_feat_sources(character, game_data):
        source = _build_feat_source(feat_source, character, game_data)
        if source is not None:
            sources.append(source)
    return sources


def _known_cantrip_names_from_sources(game_data, sources: list[dict], *, exclude_source_id: str = "") -> set[str]:
    known: set[str] = set()
    for source in sources:
        if exclude_source_id and source["source_id"] == exclude_source_id:
            continue
        for entry in source.get("granted_entries", []):
            if entry.get("kind") == "cantrip":
                known.add(str(entry.get("spell_name", "")).strip())
    return known


def get_active_spell_grant_sources(character, game_data) -> list[dict]:
    sources = _build_active_sources_raw(character, game_data)

    # Duplicate-fallback feats resolve after other sources are known.
    for source in sources:
        label = source["source_label"]
        if label not in {"Cold Caster", "Light Bringer"}:
            continue

        default_cantrip = "Ray of Frost" if label == "Cold Caster" else "Light"
        replacement_class = "Wizard" if label == "Cold Caster" else "Cleric"
        known_elsewhere = set(getattr(character, "selected_cantrips", []) or [])
        known_elsewhere.update(
            _known_cantrip_names_from_sources(
                game_data,
                sources,
                exclude_source_id=source["source_id"],
            )
        )

        if default_cantrip not in known_elsewhere:
            continue

        source["granted_entries"] = []
        source["cantrip_choice_count"] = 1
        source["cantrip_options"] = [
            spell["name"]
            for spell in getattr(game_data, "cantrips_for_class", lambda _name: [])(replacement_class)
            if str(spell.get("name", "")).strip() != default_cantrip
        ]
        selected_cantrips = _sort_spell_names(
            game_data,
            get_spell_grant_choice_value(character, source["source_id"], "cantrips", []) or [],
        )[:1]
        source["selected_cantrips"] = selected_cantrips
        for spell_name in selected_cantrips:
            source["granted_entries"].append(
                _spell_entry(source["source_id"], source["source_label"], spell_name, "cantrip")
            )

    # Potent Dragonmark augments active Dragonmark feats.
    if _has_potent_dragonmark(character, game_data):
        for mark_source_id, _mark_label, feat_name in _active_mark_feat_names(character, game_data):
            for source in sources:
                if source["source_id"] != mark_source_id:
                    continue
                source["resource_entries"].append(
                    {"label": "1 Dragonmark spell", "cadence": "1 / Short or Long Rest"}
                )
                source["expansion_spells"] = list(_MARK_FEAT_DATA[feat_name]["expansion_spells"])
                for entry in source["granted_entries"]:
                    if entry.get("kind") == "spell":
                        entry["dragonmark_eligible"] = True
                break

    # Potent Dragonmark prepared expansion spells become read-only spell entries.
    if _has_potent_dragonmark(character, game_data):
        for mark_source_id, mark_label, feat_name in _active_mark_feat_names(character, game_data):
            expansion_entries = [
                _spell_entry(
                    mark_source_id,
                    mark_label,
                    spell_name,
                    "spell",
                    dragonmark_eligible=True,
                )
                for spell_name in _MARK_FEAT_DATA[feat_name]["expansion_spells"]
            ]
            for source in sources:
                if source["source_id"] == mark_source_id:
                    existing = {
                        str(entry.get("spell_name", "")).strip()
                        for entry in source["granted_entries"]
                        if entry.get("kind") == "spell"
                    }
                    for entry in expansion_entries:
                        if entry["spell_name"] not in existing:
                            source["granted_entries"].append(entry)
                    break

    for source in sources:
        if source.get("ability_choice_required"):
            source["ability_value"] = str(
                get_spell_grant_choice_value(character, source["source_id"], "ability", "") or ""
            ).strip()
        if source["source_list_options"]:
            source["source_list_value"] = str(
                get_spell_grant_choice_value(character, source["source_id"], "source_list", "") or ""
            ).strip()

    return sources


def _class_spell_default_ability(character) -> str:
    cls = getattr(character, "character_class", None) or {}
    ability = str(cls.get("spellcasting_ability", "") or "").strip()
    return ability if ability in _SPELLCASTING_ABILITIES else ""


def apply_default_spell_grant_abilities(character, game_data) -> bool:
    changed = False
    class_ability = _class_spell_default_ability(character)
    if not class_ability:
        # Non-caster: pick highest mental stat as default for species spells
        scores = getattr(character, "ability_scores", None)
        if scores:
            best = ""
            best_val = -1
            for ab in _SPELLCASTING_ABILITIES:
                val = scores.total(ab)
                if val > best_val:
                    best_val = val
                    best = ab
            class_ability = best
    if not class_ability:
        return False

    for source in get_active_spell_grant_sources(character, game_data):
        if not source.get("ability_choice_required"):
            continue
        if source["ability_options"] != list(_SPELLCASTING_ABILITIES):
            continue
        source_id = source["source_id"]
        current = str(get_spell_grant_choice_value(character, source_id, "ability", "") or "").strip()
        if current:
            continue
        set_spell_grant_choice_value(character, source_id, "ability", class_ability)
        changed = True
    return changed


def scrub_spell_grant_choices(character, game_data) -> bool:
    changed = False
    active_sources = get_active_spell_grant_sources(character, game_data)
    active_ids = {source["source_id"] for source in active_sources}
    store = _choice_store(character, create=False)

    for source_id in list(store.keys()):
        if source_id not in active_ids:
            store.pop(source_id, None)
            changed = True

    for source in active_sources:
        source_id = source["source_id"]
        bucket = _source_choice(character, source_id, create=False)

        if source["source_list_options"]:
            value = str(bucket.get("source_list", "") or "").strip()
            if value and value not in set(source["source_list_options"]):
                bucket.pop("source_list", None)
                changed = True

        if source.get("ability_choice_required"):
            value = str(bucket.get("ability", "") or "").strip()
            valid_abilities = set(source.get("ability_options", []))
            if value and value not in valid_abilities:
                bucket.pop("ability", None)
                changed = True

        if source["cantrip_choice_count"]:
            valid = set(source["cantrip_options"])
            cleaned = [
                name
                for name in _sort_spell_names(game_data, bucket.get("cantrips", []) or [])
                if name in valid
            ][: source["cantrip_choice_count"]]
            if cleaned != _sort_spell_names(game_data, bucket.get("cantrips", []) or []):
                if cleaned:
                    bucket["cantrips"] = cleaned
                else:
                    bucket.pop("cantrips", None)
                changed = True
        else:
            if "cantrips" in bucket:
                bucket.pop("cantrips", None)
                changed = True

        if source["spell_choice_count"]:
            valid = set(source["spell_options"])
            cleaned = [
                name
                for name in _sort_spell_names(game_data, bucket.get("spells", []) or [])
                if name in valid
            ][: source["spell_choice_count"]]
            if cleaned != _sort_spell_names(game_data, bucket.get("spells", []) or []):
                if cleaned:
                    bucket["spells"] = cleaned
                else:
                    bucket.pop("spells", None)
                changed = True
        else:
            if "spells" in bucket:
                bucket.pop("spells", None)
                changed = True

        if not bucket:
            store.pop(source_id, None)
            changed = True

    fixed_cantrips = {
        entry["spell_name"]
        for source in active_sources
        for entry in source.get("granted_entries", [])
        if entry.get("kind") == "cantrip"
    }
    fixed_spells = {
        entry["spell_name"]
        for source in active_sources
        for entry in source.get("granted_entries", [])
        if entry.get("kind") == "spell"
    }
    selected_cantrips = list(getattr(character, "selected_cantrips", []) or [])
    selected_spells = list(getattr(character, "selected_spells", []) or [])
    cleaned_cantrips = [name for name in selected_cantrips if name not in fixed_cantrips]
    cleaned_spells = [name for name in selected_spells if name not in fixed_spells]
    if cleaned_cantrips != selected_cantrips:
        character.selected_cantrips = cleaned_cantrips
        changed = True
    if cleaned_spells != selected_spells:
        character.selected_spells = cleaned_spells
        changed = True

    return changed


def _resolve_cadence(character, cadence: str) -> str:
    if cadence != "PB / Long Rest":
        return cadence
    return f"{character.proficiency_bonus} / Long Rest"


def get_spell_grant_requirements(character, game_data) -> list[dict]:
    requirements: list[dict] = []
    for source in get_active_spell_grant_sources(character, game_data):
        label = source["source_label"]
        source_id = source["source_id"]
        if source["source_list_options"] and not str(
            get_spell_grant_choice_value(character, source_id, "source_list", "") or ""
        ).strip():
            requirements.append(
                {
                    "id": f"{source_id}:source_list",
                    "step_key": "spells",
                    "message": f"Choose a spell list for {label}.",
                }
            )
        if source.get("ability_choice_required") and not str(
            get_spell_grant_choice_value(character, source_id, "ability", "") or ""
        ).strip():
            requirements.append(
                {
                    "id": f"{source_id}:ability",
                    "step_key": "spells",
                    "message": f"Choose a spellcasting ability for {label}.",
                }
            )
        selected_cantrips = _sort_spell_names(
            game_data,
            get_spell_grant_choice_value(character, source_id, "cantrips", []) or [],
        )
        if source["cantrip_choice_count"] and len(selected_cantrips) < source["cantrip_choice_count"]:
            missing = source["cantrip_choice_count"] - len(selected_cantrips)
            requirements.append(
                {
                    "id": f"{source_id}:cantrips",
                    "step_key": "spells",
                    "message": f"Choose {missing} more cantrip selection(s) for {label}.",
                    "missing_count": missing,
                }
            )
        selected_spells = _sort_spell_names(
            game_data,
            get_spell_grant_choice_value(character, source_id, "spells", []) or [],
        )
        if source["spell_choice_count"] and len(selected_spells) < source["spell_choice_count"]:
            missing = source["spell_choice_count"] - len(selected_spells)
            requirements.append(
                {
                    "id": f"{source_id}:spells",
                    "step_key": "spells",
                    "message": f"Choose {missing} more spell selection(s) for {label}.",
                    "missing_count": missing,
                }
            )
    return requirements


def get_spell_grant_followup_sources(character, game_data) -> list[dict]:
    return [
        source
        for source in get_active_spell_grant_sources(character, game_data)
        if source["source_list_options"]
        or source.get("ability_choice_required")
        or source["cantrip_choice_count"]
        or source["spell_choice_count"]
    ]


def character_has_spell_step_content(character, game_data) -> bool:
    if getattr(character, "is_caster", False):
        from models.level1_class_rules import (
            get_effective_cantrips_known,
            get_effective_prepared_spells,
        )

        if (
            get_effective_cantrips_known(character) > 0
            or get_effective_prepared_spells(character) > 0
        ):
            return True
    if get_spell_grant_followup_sources(character, game_data):
        return True
    return False


def has_spellbook_entries(character, game_data) -> bool:
    return bool(get_spellbook_entries(character, game_data))


def get_extra_class_spell_options(character, game_data, *, level: int | None = None) -> list[str]:
    options: list[str] = []
    for source in get_active_spell_grant_sources(character, game_data):
        for spell_name in source.get("expansion_spells", []):
            spell = _find_spell(game_data, spell_name)
            if spell is None:
                continue
            if level is not None and int(spell.get("level", 0) or 0) != level:
                continue
            options.append(spell_name)
    return _sort_spell_names(game_data, options)


def get_selectable_class_cantrip_options(character, game_data) -> list[str]:
    class_name = str((getattr(character, "character_class", None) or {}).get("name", "") or "").strip()
    options = [
        spell["name"]
        for spell in getattr(game_data, "cantrips_for_class", lambda _name: [])(class_name)
    ]
    fixed = {
        entry["spell_name"]
        for source in get_active_spell_grant_sources(character, game_data)
        for entry in source.get("granted_entries", [])
        if entry.get("kind") == "cantrip"
    }
    return _sort_spell_names(game_data, [name for name in options if name not in fixed])


def get_selectable_class_spell_options(character, game_data, *, level: int = 1) -> list[str]:
    class_name = str((getattr(character, "character_class", None) or {}).get("name", "") or "").strip()
    options = [
        spell["name"]
        for spell in getattr(game_data, "spells_for_class", lambda _name, max_level=1: [])(class_name, max_level=level)
        if int(spell.get("level", 0) or 0) == level
    ]
    options.extend(get_extra_class_spell_options(character, game_data, level=level))
    fixed = {
        entry["spell_name"]
        for source in get_active_spell_grant_sources(character, game_data)
        for entry in source.get("granted_entries", [])
        if entry.get("kind") == "spell"
    }
    return _sort_spell_names(game_data, [name for name in options if name not in fixed])


def get_free_spell_summary_entries(character, game_data) -> list[dict]:
    entries: list[dict] = []
    for source in get_active_spell_grant_sources(character, game_data):
        source_label = source["source_label"]
        for spell_entry in source.get("granted_entries", []):
            free_cast = str(spell_entry.get("free_cast", "") or "").strip()
            if not free_cast:
                continue
            if spell_entry.get("kind") == "cantrip":
                continue
            spell_name = str(spell_entry.get("spell_name", "") or "").strip()
            entries.append(
                {
                    "label": f"{spell_name} ({source_label})",
                    "cadence": _resolve_cadence(character, free_cast),
                }
            )
        for resource_entry in source.get("resource_entries", []):
            entries.append(
                {
                    "label": resource_entry["label"],
                    "cadence": resource_entry["cadence"],
                }
            )
    return entries


def get_spellbook_entries(character, game_data) -> list[dict]:
    merged: dict[str, dict] = {}
    spell_names = set()
    spell_names.update(getattr(character, "selected_cantrips", []) or [])
    spell_names.update(getattr(character, "selected_spells", []) or [])

    for source in get_active_spell_grant_sources(character, game_data):
        for entry in source.get("granted_entries", []):
            spell_names.add(entry["spell_name"])

    for spell_name in _sort_spell_names(game_data, spell_names):
        spell = _find_spell(game_data, spell_name) or {}
        level = int(spell.get("level", 0) or 0) if spell else 0
        merged[spell_name] = {
            "spell_name": spell_name,
            "spell": spell,
            "level": level,
            "base_selected": spell_name in set(getattr(character, "selected_cantrips", []) or [])
            or spell_name in set(getattr(character, "selected_spells", []) or []),
            "source_labels": [],
            "free_casts": [],
            "ritual_only": False,
            "dragonmark_eligible": False,
            "detail_notes": [],
        }

    for source in get_active_spell_grant_sources(character, game_data):
        for entry in source.get("granted_entries", []):
            spell_name = entry["spell_name"]
            spell = _find_spell(game_data, spell_name) or {}
            inferred_level = int(spell.get("level", 0) or 0)
            if not spell and entry.get("kind") == "spell":
                inferred_level = 1
            row = merged.setdefault(
                spell_name,
                {
                    "spell_name": spell_name,
                    "spell": spell,
                    "level": inferred_level,
                    "base_selected": False,
                    "source_labels": [],
                    "free_casts": [],
                    "ritual_only": False,
                    "dragonmark_eligible": False,
                    "detail_notes": [],
                },
            )
            if not row.get("spell") and spell:
                row["spell"] = spell
            if inferred_level and not int(row.get("level", 0) or 0):
                row["level"] = inferred_level
            label = str(entry.get("source_label", "") or "").strip()
            if label and label not in row["source_labels"]:
                row["source_labels"].append(label)
            free_cast = str(entry.get("free_cast", "") or "").strip()
            if free_cast:
                resolved = _resolve_cadence(character, free_cast)
                if resolved not in row["free_casts"]:
                    row["free_casts"].append(resolved)
            if entry.get("ritual_only"):
                row["ritual_only"] = True
            if entry.get("dragonmark_eligible"):
                row["dragonmark_eligible"] = True
            note = str(entry.get("detail_note", "") or "").strip()
            if note and note not in row["detail_notes"]:
                row["detail_notes"].append(note)

    result = list(merged.values())
    result.sort(key=lambda row: (row["level"], row["spell_name"].casefold()))
    return result


def format_spellbook_entry_label(entry: dict) -> str:
    label = str(entry.get("spell_name", "") or "").strip()
    source_labels = [str(value).strip() for value in entry.get("source_labels", []) if str(value).strip()]
    if source_labels:
        label = f"{label} ({', '.join(source_labels)})"
    if entry.get("dragonmark_eligible"):
        label = f"{label} (Dragonmark)"
    return label


def get_spellbook_sections(character, game_data) -> list[tuple[str, list[dict]]]:
    grouped: dict[int, list[dict]] = {}
    for entry in get_spellbook_entries(character, game_data):
        grouped.setdefault(int(entry.get("level", 0) or 0), []).append(entry)

    sections: list[tuple[str, list[dict]]] = []
    for level in sorted(grouped.keys()):
        section_name = "Cantrips" if level == 0 else f"Level {level}"
        sections.append((section_name, grouped[level]))
    return sections
