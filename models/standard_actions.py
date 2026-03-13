"""Build standard attack actions for summary and PDF output."""

from __future__ import annotations

import json
import os
import re

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
    profs = [
        str(p).lower()
        for p in character.character_class.get("weapon_proficiencies", [])
    ]

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
    str_mod = character.ability_scores.modifier("Strength")
    dex_mod = character.ability_scores.modifier("Dexterity")
    if weapon_meta.get("ranged"):
        return dex_mod
    if weapon_meta.get("finesse"):
        return max(str_mod, dex_mod)
    return str_mod


def _weapon_actions(character) -> list[dict]:
    rows: list[dict] = []
    counts = _weapon_counts_from_texts(_selected_equipment_texts(character))

    for weapon_name, qty in sorted(counts.items()):
        meta = WEAPON_DATA.get(weapon_name)
        if not meta:
            continue

        ability_mod = _weapon_ability_mod(character, meta)
        prof = (
            character.proficiency_bonus
            if _has_weapon_proficiency(character, weapon_name, meta)
            else 0
        )
        attack_bonus = ability_mod + prof

        dmg_mod = _modifier_str(ability_mod)
        damage = f"{meta['damage']}{dmg_mod} {meta['type'].lower()}"
        if meta.get("versatile_damage"):
            damage += f" ({meta['versatile_damage']} two-handed)"

        notes_parts = ["Ranged weapon" if meta.get("ranged") else "Melee weapon"]
        if meta.get("range"):
            notes_parts.append(f"range {meta['range']}")
        if meta.get("thrown_range"):
            notes_parts.append(f"thrown {meta['thrown_range']}")
        notes = ", ".join(notes_parts)
        if qty > 1 and not meta.get("thrown_range"):
            notes += f" (x{qty})"

        rows.append(
            {
                "name": weapon_name.title(),
                "attack": _modifier_str(attack_bonus),
                "damage": damage,
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


def _cantrip_actions(character, spells_by_name: dict[str, dict]) -> list[dict]:
    rows: list[dict] = []

    cast_ability = None
    if character.character_class:
        cast_ability = character.character_class.get("spellcasting_ability")
        if not cast_ability:
            primary = character.character_class.get("primary_ability", [])
            cast_ability = primary[0] if primary else None

    if not cast_ability:
        return rows

    spell_mod = character.ability_scores.modifier(cast_ability)
    attack_bonus = _modifier_str(spell_mod + character.proficiency_bonus)

    for cantrip_name in sorted(character.selected_cantrips):
        spell = spells_by_name.get(cantrip_name)
        if not spell or not _is_attack_cantrip(spell):
            continue
        rows.append(
            {
                "name": cantrip_name,
                "attack": attack_bonus,
                "damage": _scaled_cantrip_damage(spell, character.level),
                "notes": spell.get("range", "Spell"),
                "kind": "cantrip",
            }
        )

    return rows


def build_standard_actions(
    character,
    spells_by_name: dict[str, dict] | None = None,
    weapon_options: dict[str, dict] | None = None,
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
    spell_mod = character.ability_scores.modifier(cast_ability) if cast_ability else 0
    has_true_strike = any(
        name.lower() == "true strike" for name in character.selected_cantrips
    )

    weapons = _weapon_actions(character)
    upgraded = []
    for row in weapons:
        key = row.get("weapon_key", "")
        meta = WEAPON_DATA.get(key, {})
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
            if _has_weapon_proficiency(character, key, meta)
            else 0
        )
        attack_bonus = ability_mod + prof

        die = (
            meta.get("versatile_damage")
            if use_two_handed
            else meta.get("damage", "1d4")
        )
        damage_type = meta.get("type", "Bludgeoning").lower()
        if use_true_strike:
            damage_type = f"radiant/{damage_type}"

        row["attack"] = _modifier_str(attack_bonus)
        row["damage"] = f"{die}{_modifier_str(ability_mod)} {damage_type}"
        row["can_true_strike"] = can_true_strike
        row["true_strike_active"] = use_true_strike
        row["two_handed_active"] = use_two_handed
        upgraded.append(row)

    return upgraded + _cantrip_actions(character, spells)
