"""Build standard attack actions for summary and PDF output."""

from __future__ import annotations

import json
import os
import re

from models.spell_grant_utils import get_spellbook_entries
from models.item_effects import (
    get_effective_modifier,
    get_ranged_damage_bonus,
    get_spell_attack_bonus,
    get_weapon_attack_bonus,
    get_weapon_damage_bonus,
    get_weapon_extra_damage,
)
from paths import data_dir


WEAPON_DATA = {
    "club": {
        "damage": "1d4",
        "type": "Bludgeoning",
        "category": "simple",
        "ranged": False,
        "finesse": False,
    },
    "dagger": {
        "damage": "1d4",
        "type": "Piercing",
        "category": "simple",
        "ranged": False,
        "finesse": True,
        "thrown_range": "20/60",
    },
    "greatclub": {
        "damage": "1d8",
        "type": "Bludgeoning",
        "category": "simple",
        "ranged": False,
        "finesse": False,
    },
    "handaxe": {
        "damage": "1d6",
        "type": "Slashing",
        "category": "simple",
        "ranged": False,
        "finesse": False,
        "thrown_range": "20/60",
    },
    "javelin": {
        "damage": "1d6",
        "type": "Piercing",
        "category": "simple",
        "ranged": False,
        "finesse": False,
        "thrown_range": "30/120",
    },
    "light crossbow": {
        "damage": "1d8",
        "type": "Piercing",
        "category": "simple",
        "ranged": True,
        "finesse": False,
        "range": "80/320",
    },
    "mace": {
        "damage": "1d6",
        "type": "Bludgeoning",
        "category": "simple",
        "ranged": False,
        "finesse": False,
    },
    "quarterstaff": {
        "damage": "1d6",
        "type": "Bludgeoning",
        "category": "simple",
        "ranged": False,
        "finesse": False,
        "versatile_damage": "1d8",
    },
    "scimitar": {
        "damage": "1d6",
        "type": "Slashing",
        "category": "martial",
        "ranged": False,
        "finesse": True,
    },
    "shortbow": {
        "damage": "1d6",
        "type": "Piercing",
        "category": "simple",
        "ranged": True,
        "finesse": False,
        "range": "80/320",
    },
    "shortsword": {
        "damage": "1d6",
        "type": "Piercing",
        "category": "martial",
        "ranged": False,
        "finesse": True,
    },
    "sickle": {
        "damage": "1d4",
        "type": "Slashing",
        "category": "simple",
        "ranged": False,
        "finesse": False,
    },
    "spear": {
        "damage": "1d6",
        "type": "Piercing",
        "category": "simple",
        "ranged": False,
        "finesse": False,
        "versatile_damage": "1d8",
        "thrown_range": "20/60",
    },
    "flail": {
        "damage": "1d8",
        "type": "Bludgeoning",
        "category": "martial",
        "ranged": False,
        "finesse": False,
    },
    "greataxe": {
        "damage": "1d12",
        "type": "Slashing",
        "category": "martial",
        "ranged": False,
        "finesse": False,
    },
    "greatsword": {
        "damage": "2d6",
        "type": "Slashing",
        "category": "martial",
        "ranged": False,
        "finesse": False,
    },
    "longbow": {
        "damage": "1d8",
        "type": "Piercing",
        "category": "martial",
        "ranged": True,
        "finesse": False,
        "range": "150/600",
    },
    "longsword": {
        "damage": "1d8",
        "type": "Slashing",
        "category": "martial",
        "ranged": False,
        "finesse": False,
        "versatile_damage": "1d10",
    },
    "rapier": {
        "damage": "1d8",
        "type": "Piercing",
        "category": "martial",
        "ranged": False,
        "finesse": True,
    },
}

ARMOR_DATA = {
    "padded armor": {"base": 11, "dex_cap": None, "heavy": False, "shield": False},
    "leather armor": {"base": 11, "dex_cap": None, "heavy": False, "shield": False},
    "studded leather armor": {
        "base": 12,
        "dex_cap": None,
        "heavy": False,
        "shield": False,
    },
    "hide armor": {"base": 12, "dex_cap": 2, "heavy": False, "shield": False},
    "chain shirt": {"base": 13, "dex_cap": 2, "heavy": False, "shield": False},
    "scale mail": {"base": 14, "dex_cap": 2, "heavy": False, "shield": False},
    "breastplate": {"base": 14, "dex_cap": 2, "heavy": False, "shield": False},
    "half plate armor": {"base": 15, "dex_cap": 2, "heavy": False, "shield": False},
    "ring mail": {"base": 14, "dex_cap": 0, "heavy": True, "shield": False},
    "chain mail": {"base": 16, "dex_cap": 0, "heavy": True, "shield": False},
    "splint armor": {"base": 17, "dex_cap": 0, "heavy": True, "shield": False},
    "plate armor": {"base": 18, "dex_cap": 0, "heavy": True, "shield": False},
    "shield": {"base": 2, "dex_cap": None, "heavy": False, "shield": True},
}


def _modifier_str(mod: int) -> str:
    return f"+{mod}" if mod >= 0 else str(mod)


def _selected_equipment_texts(character) -> list[str]:
    texts: list[str] = []

    if character.character_class:
        for opt in character.character_class.get("starting_equipment", []):
            if opt.get("option") == character.equipment_choice_class:
                texts.append(opt.get("items", ""))
                break

    if character.background:
        for opt in character.background.get("equipment", []):
            if opt.get("option") == character.equipment_choice_background:
                texts.append(opt.get("items", ""))
                break

    return texts


def _split_equipment_parts(texts: list[str]) -> list[tuple[str, int, str]]:
    """Return parsed parts as (normalized, qty, original)."""
    parsed: list[tuple[str, int, str]] = []
    for text in texts:
        if not text:
            continue
        cleaned = text.replace(";", " ")
        parts = [p.strip() for p in cleaned.split(",") if p.strip()]
        for part in parts:
            lower = part.lower()
            if " gp" in lower:
                continue
            lower_no_parens = re.sub(r"\([^)]*\)", "", lower)
            qty_match = re.match(r"^(\d+)\s+", lower_no_parens)
            qty = int(qty_match.group(1)) if qty_match else 1
            parsed.append((lower_no_parens.strip(), qty, part))
    return parsed


def get_selected_weapon_counts(character) -> dict[str, int]:
    """Get weapon counts from currently selected class/background equipment."""
    return _weapon_counts_from_texts(_selected_equipment_texts(character))


def get_selected_armor_counts(character) -> dict[str, int]:
    """Get armor and shield counts from currently selected equipment."""
    counts: dict[str, int] = {}
    for normalized, qty, _original in _split_equipment_parts(
        _selected_equipment_texts(character)
    ):
        for armor_name in ARMOR_DATA:
            if armor_name in normalized:
                counts[armor_name] = counts.get(armor_name, 0) + qty
    return counts


def get_selected_non_weapon_items(character) -> list[str]:
    """Get non-weapon equipment lines from currently selected bundles."""
    items: list[str] = []
    for normalized, qty, original in _split_equipment_parts(
        _selected_equipment_texts(character)
    ):
        if any(w in normalized for w in WEAPON_DATA):
            continue
        if any(a in normalized for a in ARMOR_DATA):
            continue
        text = re.sub(r"\s+", " ", original).strip()
        if not text:
            continue
        if qty > 1 and not re.match(r"^\d+\s+", text):
            text = f"{qty} {text}"
        items.append(text)
    return items


def _weapon_counts_from_texts(texts: list[str]) -> dict[str, int]:
    counts: dict[str, int] = {}

    for text in texts:
        if not text:
            continue
        cleaned = text.replace(";", " ")
        parts = [p.strip() for p in cleaned.split(",") if p.strip()]

        for part in parts:
            lower = part.lower()
            if " gp" in lower:
                continue

            # Normalize parenthetical wrappers like "Arcane Focus (Quarterstaff)"
            lower_no_parens = re.sub(r"\([^)]*\)", "", lower)
            qty_match = re.match(r"^(\d+)\s+", lower_no_parens)
            qty = int(qty_match.group(1)) if qty_match else 1

            for weapon_name in WEAPON_DATA:
                if weapon_name in lower or weapon_name in lower_no_parens:
                    counts[weapon_name] = counts.get(weapon_name, 0) + qty

    return counts


def _has_weapon_proficiency(character, weapon_name: str, weapon_meta: dict) -> bool:
    if not character.character_class:
        return False
    profs = [str(p).lower() for p in character.effective_weapon_proficiencies]

    # Specific weapon mention
    if any(weapon_name in p for p in profs):
        return True

    category = weapon_meta.get("category", "")
    if category == "simple" and any("simple" in p for p in profs):
        return True
    if category == "martial" and any("martial" in p for p in profs):
        return True

    return False


def _weapon_ability_mod(character, weapon_meta: dict) -> int:
    str_mod = get_effective_modifier(character, "Strength")
    dex_mod = get_effective_modifier(character, "Dexterity")
    if weapon_meta.get("ranged"):
        return dex_mod
    if weapon_meta.get("finesse"):
        return max(str_mod, dex_mod)
    return str_mod


def _weapon_actions(
    character, equipped_weapon_keys: set[str] | None = None
) -> list[dict]:
    rows: list[dict] = []
    counts = _weapon_counts_from_texts(_selected_equipment_texts(character))

    # Maps composite weapon key → base weapon key (for variant magic items)
    variant_base: dict[str, str] = {}

    # Merge custom inventory weapons from item browser additions.
    for ent in getattr(character, "custom_inventory", []) or []:
        if str(ent.get("category", "")) != "Weapons":
            continue
        key = str(ent.get("name", "")).strip().lower()
        variant = ent.get("variant")
        if variant:
            base_key = variant.strip().lower()
            variant_base[key] = base_key
            if base_key in WEAPON_DATA:
                counts[key] = counts.get(key, 0) + max(1, int(ent.get("qty", 1)))
        elif key in WEAPON_DATA:
            counts[key] = counts.get(key, 0) + max(1, int(ent.get("qty", 1)))

    for weapon_name, qty in sorted(counts.items()):
        if equipped_weapon_keys is not None and weapon_name not in equipped_weapon_keys:
            continue
        base_key = variant_base.get(weapon_name, weapon_name)
        meta = WEAPON_DATA.get(base_key)
        if not meta:
            continue

        ability_mod = _weapon_ability_mod(character, meta)
        prof = (
            character.proficiency_bonus
            if _has_weapon_proficiency(character, base_key, meta)
            else 0
        )
        magic_atk = get_weapon_attack_bonus(character, weapon_name)
        attack_bonus = ability_mod + prof + magic_atk

        magic_dmg = get_weapon_damage_bonus(character, weapon_name)
        ranged_dmg = get_ranged_damage_bonus(character) if meta.get("ranged") else 0
        total_dmg_mod = ability_mod + magic_dmg + ranged_dmg
        dmg_mod = _modifier_str(total_dmg_mod)
        damage = f"{meta['damage']}{dmg_mod} {meta['type'].lower()}"
        if meta.get("versatile_damage"):
            damage += f" ({meta['versatile_damage']} two-handed)"

        # Extra damage dice from magic items (e.g. Flame Tongue +2d6 fire)
        extra_dmg = get_weapon_extra_damage(character, weapon_name)
        if extra_dmg:
            damage += " + " + " + ".join(extra_dmg)

        notes_parts = ["Ranged weapon" if meta.get("ranged") else "Melee weapon"]
        if meta.get("range"):
            notes_parts.append(f"range {meta['range']}")
        if meta.get("thrown_range"):
            notes_parts.append(f"thrown {meta['thrown_range']}")
        notes = ", ".join(notes_parts)
        if qty > 1 and not meta.get("thrown_range"):
            notes += f" (x{qty})"

        if meta.get("ranged"):
            range_str = meta.get("range", "")
        elif meta.get("thrown_range"):
            range_str = f"Thrown {meta['thrown_range']}"
        else:
            range_str = "-"

        rows.append(
            {
                "name": weapon_name.title(),
                "attack": _modifier_str(attack_bonus),
                "damage": damage,
                "range": range_str,
                "notes": notes,
                "kind": "weapon",
                "weapon_key": weapon_name,
                "versatile": bool(meta.get("versatile_damage")),
                "can_true_strike": False,
            }
        )

    return rows


def _load_spells() -> dict[str, dict]:
    spells_path = os.path.join(data_dir(), "spells.json")
    if not os.path.exists(spells_path):
        return {}
    with open(spells_path, "r", encoding="utf-8") as f:
        spells = json.load(f)
    return {s.get("name", ""): s for s in spells}


def _cantrip_scale(level: int) -> int:
    if level >= 17:
        return 4
    if level >= 11:
        return 3
    if level >= 5:
        return 2
    return 1


def _parse_base_damage(spell: dict) -> tuple[str, str] | None:
    text = f"{spell.get('description', '')} {spell.get('cantrip_upgrade', '')}"
    m = re.search(r"(\d+)d(\d+)\s+([A-Za-z]+)\s+damage", text, re.IGNORECASE)
    if not m:
        return None
    return f"{m.group(1)}d{m.group(2)}", m.group(3).capitalize()


def _scaled_cantrip_damage(spell: dict, character_level: int) -> str:
    parsed = _parse_base_damage(spell)
    if not parsed:
        return "--"

    base_die, damage_type = parsed
    base_count, die_size = base_die.lower().split("d")
    count = int(base_count) * _cantrip_scale(character_level)

    upgrade_text = str(spell.get("cantrip_upgrade", "")).lower()
    if "creates two beams" in upgrade_text:
        beams = _cantrip_scale(character_level)
        if beams <= 1:
            return f"{base_die} {damage_type.lower()}"
        return f"{base_die} {damage_type.lower()} x{beams} beams"

    return f"{count}d{die_size} {damage_type.lower()}"


def _is_attack_cantrip(spell: dict) -> bool:
    if spell.get("level") != 0:
        return False
    desc = str(spell.get("description", "")).lower()
    return "spell attack" in desc


def _spellbook_cantrip_names(character, spells_by_name: dict[str, dict], game_data=None) -> list[str]:
    if game_data is not None:
        names = [
            str(entry.get("spell_name", "")).strip()
            for entry in get_spellbook_entries(character, game_data)
            if int(entry.get("level", 0) or 0) == 0
        ]
    else:
        names = list(getattr(character, "selected_cantrips", []) or [])

    unique: list[str] = []
    seen: set[str] = set()
    for name in names:
        clean = str(name or "").strip()
        if not clean or clean in seen:
            continue
        if clean not in spells_by_name:
            continue
        unique.append(clean)
        seen.add(clean)
    return sorted(unique)


def _get_active_invocations(character) -> list[tuple[str, str]]:
    """Return (invocation_name, bound_cantrip) pairs for active warlock invocations."""
    pairs: list[tuple[str, str]] = []

    # Level 1 class choices
    choices = getattr(character, "level1_class_choices", {}) or {}
    inv = str(choices.get("warlock_invocation", "")).strip()
    cantrip = str(choices.get("warlock_invocation_cantrip", "")).strip()
    if inv and cantrip:
        pairs.append((inv, cantrip))

    # Level-up invocations (from class_levels)
    replaced: set[str] = set()
    for cl in getattr(character, "class_levels", []):
        if cl.replaced_choice:
            replaced.add(cl.replaced_choice)

    for cl in getattr(character, "class_levels", []):
        for choice_name in cl.new_choices:
            if choice_name in replaced:
                continue
            sub = cl.choice_sub_selections.get(choice_name, "")
            if sub:
                pairs.append((choice_name, sub))

    return pairs


def _get_feature_pick(character, feature_name: str) -> str | None:
    """Look up a permanent feature pick across all class levels."""
    for cl in getattr(character, "class_levels", []):
        val = cl.feature_picks.get(feature_name)
        if val:
            return val
    return None


def _get_cantrip_damage_bonus(
    character, cantrip_name: str, spell: dict, game_data=None
) -> int:
    """Compute total bonus damage modifier for a cantrip from class features."""
    bonus = 0

    class_slug = ""
    if character.character_class:
        class_slug = character.character_class.get("slug", "")

    # 1. Agonizing Blast — +CHA to bound cantrip
    for inv_name, bound_cantrip in _get_active_invocations(character):
        if inv_name == "Agonizing Blast" and bound_cantrip == cantrip_name:
            bonus += get_effective_modifier(character, "Charisma")
            break

    # 2. Empowered Evocation — Evoker wizard level 10+, +INT to Evocation spells
    if class_slug == "wizard":
        sub_slug = None
        for cl in getattr(character, "class_levels", []):
            if cl.class_slug == "wizard" and cl.subclass_slug:
                sub_slug = cl.subclass_slug
        wiz_level = sum(
            1 for cl in getattr(character, "class_levels", [])
            if cl.class_slug == "wizard"
        )
        if sub_slug == "evoker" and wiz_level >= 10:
            if spell.get("school", "").lower() == "evocation":
                bonus += get_effective_modifier(character, "Intelligence")

    # 3. Potent Spellcasting (Cleric Blessed Strikes level 7+)
    if class_slug == "cleric":
        cleric_level = sum(
            1 for cl in getattr(character, "class_levels", [])
            if cl.class_slug == "cleric"
        )
        if cleric_level >= 7:
            pick = _get_feature_pick(character, "Blessed Strikes")
            if pick == "Potent Spellcasting":
                cleric_spells = spell.get("classes", [])
                if "Cleric" in cleric_spells:
                    bonus += get_effective_modifier(character, "Wisdom")

    # 4. Potent Spellcasting (Druid Elemental Fury level 7+)
    if class_slug == "druid":
        druid_level = sum(
            1 for cl in getattr(character, "class_levels", [])
            if cl.class_slug == "druid"
        )
        if druid_level >= 7:
            pick = _get_feature_pick(character, "Elemental Fury")
            if pick == "Potent Spellcasting":
                druid_spells = spell.get("classes", [])
                if "Druid" in druid_spells:
                    bonus += get_effective_modifier(character, "Wisdom")

    # 5. Elemental Affinity (Draconic Sorcery level 6+)
    if class_slug == "sorcerer":
        sub_slug = None
        for cl in getattr(character, "class_levels", []):
            if cl.class_slug == "sorcerer" and cl.subclass_slug:
                sub_slug = cl.subclass_slug
        sorc_level = sum(
            1 for cl in getattr(character, "class_levels", [])
            if cl.class_slug == "sorcerer"
        )
        if sub_slug == "draconic-sorcery" and sorc_level >= 6:
            chosen_type = _get_feature_pick(character, "Elemental Affinity")
            if chosen_type:
                parsed = _parse_base_damage(spell)
                if parsed:
                    _, dmg_type = parsed
                    if dmg_type.lower() == chosen_type.lower():
                        bonus += get_effective_modifier(character, "Charisma")

    # 6. Radiant Soul (Celestial Patron warlock level 6+)
    warlock_sub_slug = None
    warlock_level = 0
    for cl in getattr(character, "class_levels", []):
        if cl.class_slug == "warlock":
            warlock_level += 1
            if cl.subclass_slug:
                warlock_sub_slug = cl.subclass_slug
    if warlock_sub_slug == "celestial-patron" and warlock_level >= 6:
        parsed = _parse_base_damage(spell)
        if parsed:
            _, dmg_type = parsed
            if dmg_type.lower() in ("radiant", "fire"):
                bonus += get_effective_modifier(character, "Charisma")

    return bonus


def _cantrip_actions(character, spells_by_name: dict[str, dict], game_data=None) -> list[dict]:
    rows: list[dict] = []

    cast_ability = None
    if character.character_class:
        cast_ability = character.character_class.get("spellcasting_ability")
        if not cast_ability:
            primary = character.character_class.get("primary_ability", [])
            cast_ability = primary[0] if primary else None

    if not cast_ability:
        return rows

    spell_mod = get_effective_modifier(character, cast_ability)
    item_bonus = get_spell_attack_bonus(character)
    attack_bonus = _modifier_str(spell_mod + character.proficiency_bonus + item_bonus)

    for cantrip_name in _spellbook_cantrip_names(character, spells_by_name, game_data):
        spell = spells_by_name.get(cantrip_name)
        if not spell or not _is_attack_cantrip(spell):
            continue

        base_damage = _scaled_cantrip_damage(spell, character.level)
        dmg_bonus = _get_cantrip_damage_bonus(
            character, cantrip_name, spell, game_data
        )

        if dmg_bonus and base_damage != "--":
            # Insert bonus before the damage type text
            # e.g. "1d10 force" → "1d10+4 force", "1d10 force x4 beams" → "1d10+4 force x4 beams"
            parts = base_damage.split(" ", 1)
            if len(parts) == 2:
                base_damage = f"{parts[0]}{_modifier_str(dmg_bonus)} {parts[1]}"
            else:
                base_damage = f"{base_damage}{_modifier_str(dmg_bonus)}"

        rows.append(
            {
                "name": cantrip_name,
                "attack": attack_bonus,
                "damage": base_damage,
                "notes": spell.get("range", "Spell"),
                "kind": "cantrip",
            }
        )

    return rows


def build_standard_actions(
    character,
    spells_by_name: dict[str, dict] | None = None,
    game_data=None,
    weapon_options: dict[str, dict] | None = None,
    equipped_weapon_keys: set[str] | None = None,
) -> list[dict]:
    """Build standard action rows for weapons and attack cantrips."""
    spells = spells_by_name or _load_spells()
    options = weapon_options or {}

    cast_ability = None
    if character.character_class:
        cast_ability = character.character_class.get("spellcasting_ability")
        if not cast_ability:
            primary = character.character_class.get("primary_ability", [])
            cast_ability = primary[0] if primary else None
    spell_mod = get_effective_modifier(character, cast_ability) if cast_ability else 0
    known_cantrip_names = _spellbook_cantrip_names(character, spells, game_data)
    has_true_strike = any(
        name.lower() == "true strike" for name in known_cantrip_names
    )

    effective_equipped_keys = equipped_weapon_keys
    if effective_equipped_keys is None and hasattr(character, "equipped_weapons"):
        ew = getattr(character, "equipped_weapons", None)
        if ew is not None:
            effective_equipped_keys = set(
                w.lower() if isinstance(w, str) else w for w in ew
            )

    weapons = _weapon_actions(character, equipped_weapon_keys=effective_equipped_keys)

    # Build variant base mapping for custom inventory magic weapons
    variant_base: dict[str, str] = {}
    for ent in getattr(character, "custom_inventory", []) or []:
        if str(ent.get("category", "")) != "Weapons":
            continue
        variant = ent.get("variant")
        if variant:
            ckey = str(ent.get("name", "")).strip().lower()
            variant_base[ckey] = variant.strip().lower()

    upgraded = []
    for row in weapons:
        key = row.get("weapon_key", "")
        base_key = variant_base.get(key, key)
        meta = WEAPON_DATA.get(base_key, {})
        cfg = options.get(key, {})

        use_two_handed = bool(
            cfg.get("two_handed", False) and meta.get("versatile_damage")
        )
        can_true_strike = bool(has_true_strike and cast_ability)
        use_true_strike = bool(cfg.get("true_strike", False) and can_true_strike)

        ability_mod = _weapon_ability_mod(character, meta)
        if use_true_strike:
            ability_mod = spell_mod

        prof = (
            character.proficiency_bonus
            if _has_weapon_proficiency(character, base_key, meta)
            else 0
        )
        magic_atk = get_weapon_attack_bonus(character, key)
        attack_bonus = ability_mod + prof + magic_atk

        die = (
            meta.get("versatile_damage")
            if use_two_handed
            else meta.get("damage", "1d4")
        )
        damage_type = meta.get("type", "Bludgeoning").lower()
        if use_true_strike:
            damage_type = f"radiant/{damage_type}"

        magic_dmg = get_weapon_damage_bonus(character, key)
        ranged_dmg = get_ranged_damage_bonus(character) if meta.get("ranged") else 0
        total_dmg_mod = ability_mod + magic_dmg + ranged_dmg
        damage_str = f"{die}{_modifier_str(total_dmg_mod)} {damage_type}"

        extra_dmg = get_weapon_extra_damage(character, key)
        if extra_dmg:
            damage_str += " + " + " + ".join(extra_dmg)

        row["attack"] = _modifier_str(attack_bonus)
        row["damage"] = damage_str
        row["can_true_strike"] = can_true_strike
        row["true_strike_active"] = use_true_strike
        row["two_handed_active"] = use_two_handed
        upgraded.append(row)

    return upgraded + _cantrip_actions(character, spells, game_data)


# Standard combat actions available to every character
STANDARD_ACTIONS = [
    {
        "name": "Attack",
        "type": "Action",
        "description": "Make one melee or ranged attack. At certain levels, "
        "you can make more than one attack with this action.",
    },
    {
        "name": "Dash",
        "type": "Action",
        "description": "You gain extra movement equal to your speed for "
        "the current turn.",
    },
    {
        "name": "Disengage",
        "type": "Action",
        "description": "Your movement doesn't provoke opportunity attacks "
        "for the rest of the turn.",
    },
    {
        "name": "Dodge",
        "type": "Action",
        "description": "Until the start of your next turn, attack rolls "
        "against you have disadvantage (if you can see the "
        "attacker), and you make Dexterity saves with advantage.",
    },
    {
        "name": "Help",
        "type": "Action",
        "description": "Give an ally advantage on the next ability check "
        "or attack roll they make before your next turn.",
    },
    {
        "name": "Hide",
        "type": "Action",
        "description": "Make a Dexterity (Stealth) check to try to hide. "
        "If you succeed, you gain certain benefits.",
    },
    {
        "name": "Ready",
        "type": "Action",
        "description": "Prepare to act later using your reaction when a "
        "specific trigger occurs. You can ready an action, "
        "movement, or a spell (requiring concentration).",
    },
    {
        "name": "Search",
        "type": "Action",
        "description": "Make a Wisdom (Perception) or Intelligence "
        "(Investigation) check to find something hidden.",
    },
    {
        "name": "Opportunity Attack",
        "type": "Reaction",
        "description": "When a creature you can see leaves your reach, "
        "you can use your reaction to make one melee attack.",
    },
]
