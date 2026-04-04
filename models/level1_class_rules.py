"""Level 1 class creation rules and helpers.

This module centralizes the character-creation requirements that come from
level-1 class features. The GUI can render these rules, and tests can assert
against them without importing Tkinter widgets.
"""

from __future__ import annotations

import json
import os
import re
from functools import lru_cache

from models.language_utils import compute_language_sources
from models.skill_utils import compute_skill_sources
from paths import data_dir

FIGHTING_STYLE_FEAT_NAMES = [
    "Archery",
    "Blind Fighting",
    "Defense",
    "Dueling",
    "Great Weapon Fighting",
    "Interception",
    "Protection",
    "Unarmed Fighting",
]

CLASS_FEATURE_STEP_CLASSES = {
    "barbarian",
    "cleric",
    "druid",
    "fighter",
    "paladin",
    "ranger",
    "rogue",
    "warlock",
}

WARLOCK_CANTRIP_BINDING_INVOCATIONS = {
    "Agonizing Blast",
    "Eldritch Spear",
    "Repelling Blast",
}

SIMPLE_WEAPONS = {
    "Club",
    "Dagger",
    "Greatclub",
    "Handaxe",
    "Javelin",
    "Light Hammer",
    "Mace",
    "Quarterstaff",
    "Sickle",
    "Spear",
    "Dart",
    "Light Crossbow",
    "Shortbow",
    "Sling",
}

MARTIAL_WEAPONS = {
    "Battleaxe",
    "Blowgun",
    "Flail",
    "Glaive",
    "Greataxe",
    "Greatsword",
    "Halberd",
    "Hand Crossbow",
    "Heavy Crossbow",
    "Lance",
    "Longbow",
    "Longsword",
    "Maul",
    "Morningstar",
    "Musket",
    "Pike",
    "Pistol",
    "Rapier",
    "Scimitar",
    "Shortsword",
    "Trident",
    "War Pick",
    "Warhammer",
    "Whip",
}

LEVEL1_FEATURE_METADATA = {
    ("artificer", "Spellcasting"): {
        "category": "existing-step choice",
        "wizard_surface": "spells",
        "notes": "Choose cantrips and prepared spells on the Spells step.",
    },
    ("artificer", "Tinker's Magic"): {
        "category": "auto grant",
        "wizard_surface": "none",
        "notes": "Automatically grants Mending; no player choice.",
    },
    ("barbarian", "Rage"): {
        "category": "document-only",
        "wizard_surface": "none",
        "notes": "Runtime feature; no creation-time choice.",
    },
    ("barbarian", "Unarmored Defense"): {
        "category": "document-only",
        "wizard_surface": "none",
        "notes": "Passive runtime feature; no creation-time choice.",
    },
    ("barbarian", "Weapon Mastery"): {
        "category": "new class-feature choice",
        "wizard_surface": "class_features",
        "notes": "Choose two melee weapons for mastery.",
    },
    ("bard", "Bardic Inspiration"): {
        "category": "document-only",
        "wizard_surface": "none",
        "notes": "Runtime feature; no creation-time choice.",
    },
    ("bard", "Spellcasting"): {
        "category": "existing-step choice",
        "wizard_surface": "spells",
        "notes": "Choose cantrips and prepared spells on the Spells step.",
    },
    ("cleric", "Spellcasting"): {
        "category": "existing-step choice",
        "wizard_surface": "spells",
        "notes": "Choose cantrips and prepared spells on the Spells step.",
    },
    ("cleric", "Divine Order"): {
        "category": "new class-feature choice",
        "wizard_surface": "class_features",
        "notes": "Choose Protector or Thaumaturge.",
    },
    ("druid", "Spellcasting"): {
        "category": "existing-step choice",
        "wizard_surface": "spells",
        "notes": "Choose cantrips and prepared spells on the Spells step.",
    },
    ("druid", "Druidic"): {
        "category": "auto grant",
        "wizard_surface": "languages",
        "notes": "Automatically grants Druidic and Speak with Animals.",
    },
    ("druid", "Primal Order"): {
        "category": "new class-feature choice",
        "wizard_surface": "class_features",
        "notes": "Choose Magician or Warden.",
    },
    ("fighter", "Fighting Style"): {
        "category": "new class-feature choice",
        "wizard_surface": "class_features",
        "notes": "Choose one Fighting Style feat.",
    },
    ("fighter", "Second Wind"): {
        "category": "document-only",
        "wizard_surface": "none",
        "notes": "Runtime feature; no creation-time choice.",
    },
    ("fighter", "Weapon Mastery"): {
        "category": "new class-feature choice",
        "wizard_surface": "class_features",
        "notes": "Choose three weapons for mastery.",
    },
    ("monk", "Martial Arts"): {
        "category": "document-only",
        "wizard_surface": "none",
        "notes": "Runtime feature; no creation-time choice.",
    },
    ("monk", "Unarmored Defense"): {
        "category": "document-only",
        "wizard_surface": "none",
        "notes": "Passive runtime feature; no creation-time choice.",
    },
    ("paladin", "Lay On Hands"): {
        "category": "document-only",
        "wizard_surface": "none",
        "notes": "Runtime feature; no creation-time choice.",
    },
    ("paladin", "Spellcasting"): {
        "category": "existing-step choice",
        "wizard_surface": "spells",
        "notes": "Choose prepared spells on the Spells step.",
    },
    ("paladin", "Weapon Mastery"): {
        "category": "new class-feature choice",
        "wizard_surface": "class_features",
        "notes": "Choose two weapons for mastery.",
    },
    ("ranger", "Spellcasting"): {
        "category": "existing-step choice",
        "wizard_surface": "spells",
        "notes": "Choose prepared spells on the Spells step.",
    },
    ("ranger", "Favored Enemy"): {
        "category": "auto grant",
        "wizard_surface": "none",
        "notes": "Automatically grants Hunter's Mark; no player choice.",
    },
    ("ranger", "Weapon Mastery"): {
        "category": "new class-feature choice",
        "wizard_surface": "class_features",
        "notes": "Choose two weapons for mastery.",
    },
    ("rogue", "Expertise"): {
        "category": "existing-step choice",
        "wizard_surface": "skills",
        "notes": "Choose two expertise skills on the Skills step.",
    },
    ("rogue", "Sneak Attack"): {
        "category": "document-only",
        "wizard_surface": "none",
        "notes": "Runtime feature; no creation-time choice.",
    },
    ("rogue", "Thieves' Cant"): {
        "category": "existing-step choice",
        "wizard_surface": "languages",
        "notes": "Automatically grants Thieves' Cant and one extra language choice.",
    },
    ("rogue", "Weapon Mastery"): {
        "category": "new class-feature choice",
        "wizard_surface": "class_features",
        "notes": "Choose two weapons for mastery.",
    },
    ("sorcerer", "Spellcasting"): {
        "category": "existing-step choice",
        "wizard_surface": "spells",
        "notes": "Choose cantrips and prepared spells on the Spells step.",
    },
    ("sorcerer", "Innate Sorcery"): {
        "category": "document-only",
        "wizard_surface": "none",
        "notes": "Runtime feature; no creation-time choice.",
    },
    ("warlock", "Eldritch Invocations"): {
        "category": "new class-feature choice",
        "wizard_surface": "class_features",
        "notes": "Choose one invocation, plus nested selections where applicable.",
    },
    ("warlock", "Pact Magic"): {
        "category": "existing-step choice",
        "wizard_surface": "spells",
        "notes": "Choose cantrips and prepared spells on the Spells step.",
    },
    ("wizard", "Spellcasting"): {
        "category": "existing-step choice",
        "wizard_surface": "spells",
        "notes": "Choose cantrips and prepared spells on the Spells step.",
    },
    ("wizard", "Ritual Adept"): {
        "category": "document-only",
        "wizard_surface": "none",
        "notes": "Runtime feature; no creation-time choice.",
    },
    ("wizard", "Arcane Recovery"): {
        "category": "document-only",
        "wizard_surface": "none",
        "notes": "Runtime feature; no creation-time choice.",
    },
}


@lru_cache(maxsize=1)
def _load_class_choices() -> dict:
    path = os.path.join(data_dir(), "class_choices.json")
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _class_slug(character) -> str:
    return str((character.character_class or {}).get("slug", "") or "")


def _choice_map(character) -> dict:
    data = getattr(character, "level1_class_choices", {})
    return data if isinstance(data, dict) else {}


def _choice_value(character, key: str, default=None):
    return _choice_map(character).get(key, default)


def _string_choices(values) -> list[str]:
    if not isinstance(values, list):
        return []
    cleaned: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = str(value).strip()
        if text and text not in seen:
            cleaned.append(text)
            seen.add(text)
    return cleaned


def _set_choice_value(character, key: str, value):
    if not isinstance(character.level1_class_choices, dict):
        character.level1_class_choices = {}
    if value in (None, "", [], {}):
        character.level1_class_choices.pop(key, None)
    else:
        character.level1_class_choices[key] = value


def _weapon_properties(item: dict) -> set[str]:
    desc = str(item.get("description", "") or "")
    match = re.search(r"Properties:\s*(.+?);\s*Mastery:", desc, re.IGNORECASE)
    if not match:
        return set()
    return {part.strip() for part in match.group(1).split(",") if part.strip()}


def _real_weapon_items(game_data) -> list[dict]:
    real_items: list[dict] = []
    for item in getattr(game_data, "items", []):
        if item.get("category") != "Weapons":
            continue
        name = str(item.get("name", "")).strip()
        if not name or name not in SIMPLE_WEAPONS | MARTIAL_WEAPONS:
            continue
        desc = str(item.get("description", "") or "")
        if "Damage:" not in desc or "Mastery:" not in desc:
            continue
        real_items.append(item)
    return real_items


def _sorted_names(items: list[str]) -> list[str]:
    return sorted({name for name in items if name}, key=str.casefold)


def _melee_weapon_names(game_data) -> list[str]:
    names: list[str] = []
    for item in _real_weapon_items(game_data):
        props = _weapon_properties(item)
        if not any(prop.startswith("Ammunition") for prop in props):
            names.append(item["name"])
    return _sorted_names(names)


def get_weapon_mastery_options(character, game_data) -> list[str]:
    slug = _class_slug(character)
    real_items = _real_weapon_items(game_data)

    if slug == "barbarian":
        return _melee_weapon_names(game_data)

    if slug in {"fighter", "paladin", "ranger"}:
        return _sorted_names([item["name"] for item in real_items])

    if slug == "rogue":
        options: list[str] = []
        for item in real_items:
            name = item["name"]
            props = _weapon_properties(item)
            if name in SIMPLE_WEAPONS:
                options.append(name)
                continue
            if name in MARTIAL_WEAPONS and (
                "Finesse" in props or "Light" in props
            ):
                options.append(name)
        return _sorted_names(options)

    return []


def get_weapon_mastery_count(character) -> int:
    return {
        "barbarian": 2,
        "fighter": 3,
        "paladin": 2,
        "ranger": 2,
        "rogue": 2,
    }.get(_class_slug(character), 0)


def get_available_fighting_styles(game_data) -> list[dict]:
    feats = {feat.get("name"): feat for feat in getattr(game_data, "feats", [])}
    return [feats[name] for name in FIGHTING_STYLE_FEAT_NAMES if name in feats]


def get_available_order_options(character) -> list[dict]:
    cls = character.character_class or {}
    slug = cls.get("slug", "")
    if slug not in {"cleric", "druid"}:
        return []
    options = []
    for feature in cls.get("level_1_features", []):
        name = str(feature.get("name", "")).strip()
        if name:
            options.append(
                {
                    "name": name,
                    "description": str(feature.get("description", "") or "").strip(),
                }
            )
    return options


def get_available_warlock_invocations() -> list[dict]:
    config = _load_class_choices().get("warlock", {})
    options: list[dict] = []
    for option in config.get("options", []):
        if option.get("prerequisite_level"):
            continue
        if option.get("prerequisite_feature"):
            continue
        options.append(option)
    return options


def get_available_origin_feats(game_data) -> list[dict]:
    result = []
    for feat in getattr(game_data, "feats", []):
        if str(feat.get("category", "")).strip().lower() == "origin":
            result.append(feat)
    return sorted(result, key=lambda feat: str(feat.get("name", "")).casefold())


def get_tome_cantrip_options(game_data) -> list[str]:
    names = []
    for spell in getattr(game_data, "spells", []):
        if spell.get("level") == 0:
            names.append(str(spell.get("name", "")).strip())
    return _sorted_names(names)


def get_tome_ritual_options(game_data) -> list[str]:
    names = []
    for spell in getattr(game_data, "spells", []):
        if spell.get("level") == 1 and spell.get("ritual"):
            names.append(str(spell.get("name", "")).strip())
    return _sorted_names(names)


def _find_spell(game_data, spell_name: str) -> dict | None:
    lower_name = spell_name.strip().casefold()
    for spell in getattr(game_data, "spells", []):
        if str(spell.get("name", "")).strip().casefold() == lower_name:
            return spell
    return None


def _is_damage_cantrip(spell: dict | None) -> bool:
    if not spell or spell.get("level") != 0:
        return False
    text = " ".join(
        [
            str(spell.get("description", "") or ""),
            str(spell.get("cantrip_upgrade", "") or ""),
            str(spell.get("higher_levels", "") or ""),
        ]
    ).lower()
    if "damage" in text:
        return True
    return "takes " in text and ("fire" in text or "cold" in text or "force" in text)


def get_warlock_invocation_binding_options(character, game_data) -> list[str]:
    options: list[str] = []
    for spell_name in getattr(character, "selected_cantrips", []):
        spell = _find_spell(game_data, spell_name)
        if spell and _is_damage_cantrip(spell):
            options.append(spell_name)
    return _sorted_names(options)


def get_effective_cantrips_known(character) -> int:
    cls = character.character_class or {}
    total = int(cls.get("cantrips_known") or 0)
    slug = cls.get("slug", "")
    if slug == "cleric" and _choice_value(character, "divine_order") == "Thaumaturge":
        total += 1
    if slug == "druid" and _choice_value(character, "primal_order") == "Magician":
        total += 1
    return total


def get_effective_prepared_spells(character) -> int:
    cls = character.character_class or {}
    return int(cls.get("spells_prepared") or 0)


def get_auto_level1_cantrips(character) -> list[str]:
    if _class_slug(character) == "artificer":
        return ["Mending"]
    return []


def get_auto_level1_prepared_spells(character) -> list[str]:
    slug = _class_slug(character)
    if slug == "druid":
        return ["Speak with Animals"]
    if slug == "ranger":
        return ["Hunter's Mark"]
    return []


def get_effective_weapon_proficiencies(character) -> list[str]:
    cls = character.character_class or {}
    profs = [str(p).strip() for p in cls.get("weapon_proficiencies", []) if str(p).strip()]
    slug = cls.get("slug", "")
    if slug == "cleric" and _choice_value(character, "divine_order") == "Protector":
        profs.append("Martial weapons")
    if slug == "druid" and _choice_value(character, "primal_order") == "Warden":
        profs.append("Martial weapons")
    return _sorted_names(profs)


def get_effective_armor_proficiencies(character) -> list[str]:
    cls = character.character_class or {}
    profs = [str(p).strip() for p in cls.get("armor_proficiencies", []) if str(p).strip()]
    slug = cls.get("slug", "")
    if slug == "cleric" and _choice_value(character, "divine_order") == "Protector":
        profs.append("Heavy armor")
    if slug == "druid" and _choice_value(character, "primal_order") == "Warden":
        profs.append("Medium armor")
    return _sorted_names(profs)


def get_level1_skill_bonus(character, skill_display_name: str) -> int:
    slug = _class_slug(character)
    wisdom_bonus = max(1, character.ability_scores.modifier("Wisdom"))
    if slug == "cleric" and _choice_value(character, "divine_order") == "Thaumaturge":
        if skill_display_name in {"Arcana", "Religion"}:
            return wisdom_bonus
    if slug == "druid" and _choice_value(character, "primal_order") == "Magician":
        if skill_display_name in {"Arcana", "Nature"}:
            return wisdom_bonus
    return 0


def scrub_level1_class_choices(character, game_data) -> bool:
    """Remove stale class feature selections after upstream choices change."""
    changed = False
    slug = _class_slug(character)
    choices = dict(_choice_map(character))
    valid_keys = {
        "divine_order": slug == "cleric",
        "primal_order": slug == "druid",
        "fighting_style": slug == "fighter",
        "weapon_mastery": slug in {"barbarian", "fighter", "paladin", "ranger", "rogue"},
        "warlock_invocation": slug == "warlock",
        "warlock_invocation_cantrip": slug == "warlock",
        "warlock_tome_cantrips": slug == "warlock",
        "warlock_tome_rituals": slug == "warlock",
        "warlock_lessons_feat": slug == "warlock",
    }

    for key, is_valid in valid_keys.items():
        if not is_valid and key in choices:
            choices.pop(key, None)
            changed = True

    if slug == "cleric":
        valid_orders = {opt["name"] for opt in get_available_order_options(character)}
        if choices.get("divine_order") not in valid_orders:
            choices.pop("divine_order", None)
            changed = True

    if slug == "druid":
        valid_orders = {opt["name"] for opt in get_available_order_options(character)}
        if choices.get("primal_order") not in valid_orders:
            choices.pop("primal_order", None)
            changed = True

    if slug == "fighter":
        valid_styles = {feat["name"] for feat in get_available_fighting_styles(game_data)}
        if choices.get("fighting_style") not in valid_styles:
            choices.pop("fighting_style", None)
            changed = True

    if slug in {"barbarian", "fighter", "paladin", "ranger", "rogue"}:
        valid_weapons = set(get_weapon_mastery_options(character, game_data))
        valid_count = get_weapon_mastery_count(character)
        cleaned = [
            weapon for weapon in _string_choices(choices.get("weapon_mastery", []))
            if weapon in valid_weapons
        ][:valid_count]
        if cleaned != _string_choices(choices.get("weapon_mastery", [])):
            if cleaned:
                choices["weapon_mastery"] = cleaned
            else:
                choices.pop("weapon_mastery", None)
            changed = True

    if slug == "warlock":
        valid_invocations = {opt["name"] for opt in get_available_warlock_invocations()}
        invocation = choices.get("warlock_invocation")
        if invocation not in valid_invocations:
            invocation = None
            for key in (
                "warlock_invocation",
                "warlock_invocation_cantrip",
                "warlock_tome_cantrips",
                "warlock_tome_rituals",
                "warlock_lessons_feat",
            ):
                if key in choices:
                    choices.pop(key, None)
                    changed = True

        if invocation not in WARLOCK_CANTRIP_BINDING_INVOCATIONS:
            if "warlock_invocation_cantrip" in choices:
                choices.pop("warlock_invocation_cantrip", None)
                changed = True
        else:
            valid_bindings = set(get_warlock_invocation_binding_options(character, game_data))
            if choices.get("warlock_invocation_cantrip") not in valid_bindings:
                choices.pop("warlock_invocation_cantrip", None)
                changed = True

        if invocation != "Pact of the Tome":
            for key in ("warlock_tome_cantrips", "warlock_tome_rituals"):
                if key in choices:
                    choices.pop(key, None)
                    changed = True
        else:
            valid_cantrips = set(get_tome_cantrip_options(game_data))
            cleaned_cantrips = [
                name for name in _string_choices(choices.get("warlock_tome_cantrips", []))
                if name in valid_cantrips
            ][:3]
            if cleaned_cantrips != _string_choices(choices.get("warlock_tome_cantrips", [])):
                if cleaned_cantrips:
                    choices["warlock_tome_cantrips"] = cleaned_cantrips
                else:
                    choices.pop("warlock_tome_cantrips", None)
                changed = True

            valid_rituals = set(get_tome_ritual_options(game_data))
            cleaned_rituals = [
                name for name in _string_choices(choices.get("warlock_tome_rituals", []))
                if name in valid_rituals
            ][:2]
            if cleaned_rituals != _string_choices(choices.get("warlock_tome_rituals", [])):
                if cleaned_rituals:
                    choices["warlock_tome_rituals"] = cleaned_rituals
                else:
                    choices.pop("warlock_tome_rituals", None)
                changed = True

        if invocation != "Lessons of the First Ones":
            if "warlock_lessons_feat" in choices:
                choices.pop("warlock_lessons_feat", None)
                changed = True
        else:
            valid_feats = {feat["name"] for feat in get_available_origin_feats(game_data)}
            if choices.get("warlock_lessons_feat") not in valid_feats:
                choices.pop("warlock_lessons_feat", None)
                changed = True

    if changed:
        character.level1_class_choices = choices
    return changed


def requires_level1_class_features_step(character, game_data=None) -> bool:
    return _class_slug(character) in CLASS_FEATURE_STEP_CLASSES


def _requirement(
    req_id: str,
    feature_name: str,
    step_key: str,
    message: str,
    *,
    missing_count: int | None = None,
):
    data = {
        "id": req_id,
        "feature_name": feature_name,
        "step_key": step_key,
        "message": message,
    }
    if missing_count is not None:
        data["missing_count"] = missing_count
    return data


def get_unmet_level1_class_requirements(character, game_data, step_key: str | None = None) -> list[dict]:
    """Return unresolved level-1 class requirements for character creation."""
    scrub_level1_class_choices(character, game_data)

    cls = character.character_class or {}
    slug = cls.get("slug", "")
    if not slug:
        return []

    requirements: list[dict] = []

    skill_sources = compute_skill_sources(character)
    skill_missing = max(0, skill_sources["choose_count"] - len(character.selected_skills))
    if skill_missing:
        requirements.append(
            _requirement(
                "class-skills",
                "Class Skills",
                "skills",
                f"Choose {skill_missing} more class skill selection(s).",
                missing_count=skill_missing,
            )
        )

    expertise_missing = int(skill_sources.get("expertise_missing_count", 0) or 0)
    if expertise_missing:
        requirements.append(
            _requirement(
                "rogue-expertise",
                "Expertise",
                "skills",
                f"Choose {expertise_missing} more Expertise selection(s).",
                missing_count=expertise_missing,
            )
        )

    language_sources = compute_language_sources(character)
    language_missing = max(
        0,
        int(language_sources.get("free_count", 0) or 0)
        - len(getattr(character, "chosen_languages", []) or []),
    )
    if language_missing:
        requirements.append(
            _requirement(
                "class-languages",
                "Languages",
                "languages",
                f"Choose {language_missing} more language selection(s).",
                missing_count=language_missing,
            )
        )

    cantrip_target = get_effective_cantrips_known(character)
    cantrip_missing = max(0, cantrip_target - len(getattr(character, "selected_cantrips", []) or []))
    if cantrip_missing:
        requirements.append(
            _requirement(
                "class-cantrips",
                "Spellcasting",
                "spells",
                f"Choose {cantrip_missing} more cantrip(s).",
                missing_count=cantrip_missing,
            )
        )

    spell_target = get_effective_prepared_spells(character)
    spell_missing = max(0, spell_target - len(getattr(character, "selected_spells", []) or []))
    if spell_missing:
        requirements.append(
            _requirement(
                "class-spells",
                "Spellcasting",
                "spells",
                f"Choose {spell_missing} more prepared spell(s).",
                missing_count=spell_missing,
            )
        )

    valid_class_equipment = {
        str(option.get("option", "")).strip()
        for option in cls.get("starting_equipment", [])
        if str(option.get("option", "")).strip()
    }
    if valid_class_equipment and str(getattr(character, "equipment_choice_class", "") or "").strip() not in valid_class_equipment:
        requirements.append(
            _requirement(
                "class-equipment",
                "Starting Equipment",
                "equipment",
                "Choose a class starting equipment option.",
            )
        )

    choices = _choice_map(character)

    if slug == "cleric" and not choices.get("divine_order"):
        requirements.append(
            _requirement(
                "divine-order",
                "Divine Order",
                "class_features",
                "Choose a Divine Order.",
            )
        )

    if slug == "druid" and not choices.get("primal_order"):
        requirements.append(
            _requirement(
                "primal-order",
                "Primal Order",
                "class_features",
                "Choose a Primal Order.",
            )
        )

    if slug == "fighter" and not choices.get("fighting_style"):
        requirements.append(
            _requirement(
                "fighting-style",
                "Fighting Style",
                "class_features",
                "Choose a Fighting Style.",
            )
        )

    mastery_count = get_weapon_mastery_count(character)
    if mastery_count:
        selected_masteries = _string_choices(choices.get("weapon_mastery", []))
        if len(selected_masteries) < mastery_count:
            requirements.append(
                _requirement(
                    "weapon-mastery",
                    "Weapon Mastery",
                    "class_features",
                    f"Choose {mastery_count} weapon mastery selection(s).",
                    missing_count=mastery_count - len(selected_masteries),
                )
            )

    if slug == "warlock":
        invocation = str(choices.get("warlock_invocation", "")).strip()
        if not invocation:
            requirements.append(
                _requirement(
                    "warlock-invocation",
                    "Eldritch Invocations",
                    "class_features",
                    "Choose an Eldritch Invocation.",
                )
            )
        elif invocation in WARLOCK_CANTRIP_BINDING_INVOCATIONS:
            binding = str(choices.get("warlock_invocation_cantrip", "")).strip()
            if not binding:
                requirements.append(
                    _requirement(
                        "warlock-invocation-cantrip",
                        invocation,
                        "spells",
                        f"Choose a damage-dealing Warlock cantrip for {invocation}.",
                    )
                )
        elif invocation == "Pact of the Tome":
            tome_cantrips = _string_choices(choices.get("warlock_tome_cantrips", []))
            if len(tome_cantrips) < 3:
                requirements.append(
                    _requirement(
                        "warlock-tome-cantrips",
                        "Pact of the Tome",
                        "class_features",
                        "Choose 3 Pact of the Tome cantrips.",
                        missing_count=3 - len(tome_cantrips),
                    )
                )
            tome_rituals = _string_choices(choices.get("warlock_tome_rituals", []))
            if len(tome_rituals) < 2:
                requirements.append(
                    _requirement(
                        "warlock-tome-rituals",
                        "Pact of the Tome",
                        "class_features",
                        "Choose 2 Pact of the Tome ritual spells.",
                        missing_count=2 - len(tome_rituals),
                    )
                )
        elif invocation == "Lessons of the First Ones":
            if not str(choices.get("warlock_lessons_feat", "")).strip():
                requirements.append(
                    _requirement(
                        "warlock-lessons-feat",
                        "Lessons of the First Ones",
                        "class_features",
                        "Choose an Origin feat granted by Lessons of the First Ones.",
                    )
                )

    if step_key is None:
        return requirements
    return [req for req in requirements if req["step_key"] == step_key]


def get_level1_feature_catalog(game_data) -> list[dict]:
    """Return the documented level-1 features for each class."""
    catalog: list[dict] = []
    classes = sorted(getattr(game_data, "classes", []), key=lambda cls: cls.get("name", ""))
    for cls in classes:
        slug = str(cls.get("slug", "")).strip()
        progression = game_data.get_level_data(slug, 1)
        if not progression:
            continue

        seen: set[str] = set()
        feature_names: list[str] = []
        for feature in progression.get("feature_details", []):
            name = str(feature.get("name", "")).strip()
            if name and name not in seen:
                feature_names.append(name)
                seen.add(name)
        for name in progression.get("features", []):
            clean = str(name).strip()
            if clean and clean != "-" and clean not in seen:
                feature_names.append(clean)
                seen.add(clean)

        for feature_name in feature_names:
            metadata = LEVEL1_FEATURE_METADATA.get((slug, feature_name), {})
            catalog.append(
                {
                    "class_name": cls.get("name", slug.title()),
                    "class_slug": slug,
                    "feature_name": feature_name,
                    "category": metadata.get("category", "document-only"),
                    "wizard_surface": metadata.get("wizard_surface", "none"),
                    "notes": metadata.get("notes", ""),
                }
            )
    return catalog


def summarize_level1_class_choices(character) -> list[str]:
    """Return short summary lines for selected level-1 class feature choices."""
    choices = _choice_map(character)
    lines: list[str] = []
    if choices.get("divine_order"):
        lines.append(f"Divine Order: {choices['divine_order']}")
    if choices.get("primal_order"):
        lines.append(f"Primal Order: {choices['primal_order']}")
    if choices.get("fighting_style"):
        lines.append(f"Fighting Style: {choices['fighting_style']}")
    masteries = _string_choices(choices.get("weapon_mastery", []))
    if masteries:
        lines.append(f"Weapon Mastery: {', '.join(masteries)}")
    if choices.get("warlock_invocation"):
        lines.append(f"Eldritch Invocation: {choices['warlock_invocation']}")
    if choices.get("warlock_invocation_cantrip"):
        lines.append(
            f"Invocation Cantrip: {choices['warlock_invocation_cantrip']}"
        )
    tome_cantrips = _string_choices(choices.get("warlock_tome_cantrips", []))
    if tome_cantrips:
        lines.append(f"Pact of the Tome Cantrips: {', '.join(tome_cantrips)}")
    tome_rituals = _string_choices(choices.get("warlock_tome_rituals", []))
    if tome_rituals:
        lines.append(f"Pact of the Tome Rituals: {', '.join(tome_rituals)}")
    if choices.get("warlock_lessons_feat"):
        lines.append(
            f"Lessons of the First Ones: {choices['warlock_lessons_feat']}"
        )
    return lines


def _rogue_level1_expertise_choices(character) -> list[str]:
    for cl in getattr(character, "class_levels", []):
        if cl.class_slug == "rogue" and cl.class_level == 1:
            return _string_choices(getattr(cl, "new_expertise", []))
    return []


def _selected_class_equipment_line(character) -> str:
    choice = str(getattr(character, "equipment_choice_class", "") or "").strip()
    if not choice:
        return ""
    for option in (character.character_class or {}).get("starting_equipment", []):
        if str(option.get("option", "")).strip() != choice:
            continue
        items = str(option.get("items", "") or "").strip()
        if items:
            return f"Starting Equipment: Option {choice} - {items}"
        return f"Starting Equipment: Option {choice}"
    return f"Starting Equipment: Option {choice}"


def get_level1_creation_choice_lines(character) -> list[str]:
    """Return user-facing summary lines for level-1 creation choices."""
    lines: list[str] = []
    selected_skills = _string_choices(getattr(character, "selected_skills", []))
    if selected_skills:
        lines.append(f"Class Skills: {', '.join(selected_skills)}")

    expertise = _rogue_level1_expertise_choices(character)
    if expertise:
        lines.append(f"Expertise: {', '.join(expertise)}")

    selected_cantrips = _string_choices(getattr(character, "selected_cantrips", []))
    if selected_cantrips:
        lines.append(f"Chosen Cantrips: {', '.join(selected_cantrips)}")

    selected_spells = _string_choices(getattr(character, "selected_spells", []))
    if selected_spells:
        lines.append(f"Prepared Spells: {', '.join(selected_spells)}")

    chosen_languages = _string_choices(getattr(character, "chosen_languages", []))
    if chosen_languages:
        lines.append(f"Chosen Languages: {', '.join(chosen_languages)}")

    equipment_line = _selected_class_equipment_line(character)
    if equipment_line:
        lines.append(equipment_line)

    return lines


def get_level1_feature_choice_annotations(character) -> dict[str, list[str]]:
    """Return extra display lines for feature cards based on stored level-1 choices."""
    choices = _choice_map(character)
    annotations: dict[str, list[str]] = {}

    if choices.get("divine_order"):
        annotations["Divine Order"] = [
            f"Selected Order: {choices['divine_order']}"
        ]
    if choices.get("primal_order"):
        annotations["Primal Order"] = [
            f"Selected Order: {choices['primal_order']}"
        ]
    if choices.get("fighting_style"):
        annotations["Fighting Style"] = [
            f"Selected Fighting Style: {choices['fighting_style']}"
        ]

    weapon_mastery = _string_choices(choices.get("weapon_mastery", []))
    if weapon_mastery:
        annotations["Weapon Mastery"] = [
            f"Selected Weapons: {', '.join(weapon_mastery)}"
        ]

    expertise = _rogue_level1_expertise_choices(character)
    if expertise:
        annotations["Expertise"] = [
            f"Selected Skills: {', '.join(expertise)}"
        ]

    invocation = str(choices.get("warlock_invocation", "") or "").strip()
    if invocation:
        lines = [f"Selected Invocation: {invocation}"]
        if choices.get("warlock_invocation_cantrip"):
            lines.append(
                f"Invocation Cantrip: {choices['warlock_invocation_cantrip']}"
            )
        tome_cantrips = _string_choices(choices.get("warlock_tome_cantrips", []))
        if tome_cantrips:
            lines.append(f"Tome Cantrips: {', '.join(tome_cantrips)}")
        tome_rituals = _string_choices(choices.get("warlock_tome_rituals", []))
        if tome_rituals:
            lines.append(f"Tome Rituals: {', '.join(tome_rituals)}")
        if choices.get("warlock_lessons_feat"):
            lines.append(f"Granted Origin Feat: {choices['warlock_lessons_feat']}")
        annotations["Eldritch Invocations"] = lines

    return annotations


def augment_level1_feature_description(
    feature_name: str,
    description: str,
    character,
) -> str:
    """Append selected level-1 choices to a feature description when relevant."""
    notes = get_level1_feature_choice_annotations(character).get(feature_name, [])
    if not notes:
        return description

    parts: list[str] = []
    clean_description = str(description or "").strip()
    if clean_description:
        parts.append(clean_description)
    for note in notes:
        clean_note = str(note).strip()
        if not clean_note:
            continue
        if not clean_note.endswith("."):
            clean_note = f"{clean_note}."
        parts.append(clean_note)
    return "\n\n".join(parts)
