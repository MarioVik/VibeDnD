"""Centralized magic item stat effects registry.

Maps item names to structured stat effects. Helper functions query which
effects are currently active for a character based on equip/attune state.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ItemEffect:
    """A single stat effect granted by a magic item."""

    effect_type: str
    # int for flat bonuses, str for dice like "2d6 fire" or "Strength:19"
    value: int | str = 0
    requires_attunement: bool = False
    # Optional note shown in damage/notes, e.g. "vs dragons"
    condition: str | None = None


# ─── Effect type constants ────────────────────────────────────────────
WEAPON_ATTACK_DAMAGE = "weapon_attack_damage"
EXTRA_WEAPON_DAMAGE = "extra_weapon_damage"
AC_BONUS = "ac_bonus"
AC_BONUS_ARMOR = "ac_bonus_armor"
AC_BONUS_SHIELD = "ac_bonus_shield"
AC_BONUS_UNARMORED = "ac_bonus_unarmored"
SPELL_ATTACK = "spell_attack"
SPELL_SAVE_DC = "spell_save_dc"
SAVE_BONUS = "save_bonus"
ABILITY_CHECK_BONUS = "ability_check_bonus"
ABILITY_SET = "ability_set"
DAMAGE_BONUS_RANGED = "damage_bonus_ranged"
INITIATIVE_BONUS = "initiative_bonus"

# ─── Item Effects Registry ────────────────────────────────────────────
# Keys are lowercase item names as they appear in custom_inventory name,
# equipped_weapons, equipped_armor, or attuned_items.

ITEM_EFFECTS: dict[str, list[ItemEffect]] = {}


def _w(bonus: int, attune: bool = False) -> list[ItemEffect]:
    """Shorthand for weapon with +N attack and damage."""
    return [ItemEffect(WEAPON_ATTACK_DAMAGE, bonus, requires_attunement=attune)]


def _w_extra(
    bonus: int, extra: str, attune: bool = True, condition: str | None = None
) -> list[ItemEffect]:
    """Weapon with +N and extra damage dice."""
    effects = [ItemEffect(WEAPON_ATTACK_DAMAGE, bonus, requires_attunement=attune)]
    effects.append(
        ItemEffect(
            EXTRA_WEAPON_DAMAGE, extra,
            requires_attunement=attune, condition=condition,
        )
    )
    return effects


def _register(name: str, effects: list[ItemEffect]):
    ITEM_EFFECTS[name.lower()] = effects


# ─── +N Weapons, Armor, Shields, Ammunition ──────────────────────────
for n in (1, 2, 3):
    _register(f"weapon, +{n}", _w(n))
    _register(f"armor, +{n}", [ItemEffect(AC_BONUS_ARMOR, n)])
    _register(f"shield, +{n}", [ItemEffect(AC_BONUS_SHIELD, n)])
    _register(f"ammunition, +{n}", _w(n))

# +N Wand of the War Mage
for n in (1, 2, 3):
    _register(f"wand of the war mage, +{n}", [
        ItemEffect(SPELL_ATTACK, n, requires_attunement=True),
    ])

# +N Rod of the Pact Keeper
for n in (1, 2, 3):
    _register(f"rod of the pact keeper, +{n}", [
        ItemEffect(SPELL_ATTACK, n, requires_attunement=True),
        ItemEffect(SPELL_SAVE_DC, n, requires_attunement=True),
    ])

# +N Wraps of Unarmed Power (counted as weapons)
for n in (1, 2, 3):
    _register(f"wraps of unarmed power, +{n}", _w(n, attune=True))

# ─── Named Weapons ───────────────────────────────────────────────────
_register("berserker axe", _w(1, attune=True))
_register("dagger of venom", _w(1))
_register("dancing sword", _w(1, attune=True))
_register("defender", _w(3, attune=True))
_register("dragon slayer", _w_extra(1, "3d6", attune=False, condition="vs dragons"))
_register("flame tongue", _w_extra(0, "2d6 fire", attune=True))
_register("frost brand", _w_extra(0, "1d6 cold", attune=True))
_register("giant slayer", _w_extra(1, "2d6", attune=False, condition="vs giants"))
_register("holy avenger", _w_extra(3, "2d10 radiant", attune=True, condition="vs fiends/undead"))
_register("javelin of lightning", _w(1))
_register("luck blade", _w(1, attune=True))
_register("mace of disruption", _w_extra(0, "2d6 radiant", attune=True, condition="vs fiends/undead"))
_register("mace of smiting", _w_extra(1, "2d6", attune=False, condition="vs constructs"))
_register("mace of terror", _w(1, attune=True))
_register("moon-touched sword", _w(0))
_register("nine lives stealer", _w(2, attune=True))
_register("oathbow", _w_extra(0, "3d6 piercing", attune=True, condition="vs sworn enemy"))
_register("scimitar of speed", _w(2, attune=True))
_register("staff of striking", _w(3, attune=True))
_register("staff of the woodlands", _w(2, attune=True))
_register("sun blade", _w(2, attune=True))
_register("sword of answering", _w(3, attune=True))
_register("sword of kas", _w_extra(3, "2d10 necrotic", attune=True))
_register("sword of life stealing", _w(0, attune=True))
_register("sword of sharpness", _w(0, attune=True))
_register("sword of wounding", _w(0, attune=True))
_register("trident of fish command", _w(1, attune=True))
_register("vicious weapon", _w_extra(0, "2d6", attune=False, condition="on nat 20"))
_register("vorpal sword", _w(3, attune=True))
_register("weapon of warning", _w(0, attune=True))

# ─── Named Armor / Shields ───────────────────────────────────────────
_register("adamantine armor", [ItemEffect(AC_BONUS_ARMOR, 0)])
_register("animated shield", [ItemEffect(AC_BONUS_SHIELD, 0, requires_attunement=True)])
_register("demon armor", [ItemEffect(AC_BONUS_ARMOR, 1, requires_attunement=True)])
_register("dragon scale mail", [ItemEffect(AC_BONUS_ARMOR, 1, requires_attunement=True)])
_register("dwarven plate", [ItemEffect(AC_BONUS_ARMOR, 2)])
_register("elven chain", [ItemEffect(AC_BONUS_ARMOR, 1)])
_register("glamoured studded leather", [ItemEffect(AC_BONUS_ARMOR, 1)])
_register("mithral armor", [ItemEffect(AC_BONUS_ARMOR, 0)])
_register("plate armor of etherealness", [ItemEffect(AC_BONUS_ARMOR, 0, requires_attunement=True)])
_register("repulsion shield", [ItemEffect(AC_BONUS_SHIELD, 1, requires_attunement=True)])
_register("sentinel shield", [ItemEffect(AC_BONUS_SHIELD, 0)])
_register("shield of missile attraction", [ItemEffect(AC_BONUS_SHIELD, 0, requires_attunement=True)])
_register("spellguard shield", [ItemEffect(AC_BONUS_SHIELD, 0, requires_attunement=True)])

# ─── AC / Save Bonus Items ───────────────────────────────────────────
_register("ring of protection", [
    ItemEffect(AC_BONUS, 1, requires_attunement=True),
    ItemEffect(SAVE_BONUS, 1, requires_attunement=True),
])
_register("cloak of protection", [
    ItemEffect(AC_BONUS, 1, requires_attunement=True),
    ItemEffect(SAVE_BONUS, 1, requires_attunement=True),
])
_register("bracers of defense", [
    ItemEffect(AC_BONUS_UNARMORED, 2, requires_attunement=True),
])
_register("staff of power", [
    ItemEffect(AC_BONUS, 2, requires_attunement=True),
    ItemEffect(SAVE_BONUS, 2, requires_attunement=True),
    ItemEffect(SPELL_ATTACK, 2, requires_attunement=True),
    ItemEffect(SPELL_SAVE_DC, 2, requires_attunement=True),
    ItemEffect(WEAPON_ATTACK_DAMAGE, 2, requires_attunement=True),
])
_register("staff of the magi", [
    ItemEffect(AC_BONUS, 0, requires_attunement=True),
    ItemEffect(SAVE_BONUS, 0, requires_attunement=True),
    ItemEffect(SPELL_ATTACK, 2, requires_attunement=True),
    ItemEffect(SPELL_SAVE_DC, 2, requires_attunement=True),
    ItemEffect(WEAPON_ATTACK_DAMAGE, 2, requires_attunement=True),
])
_register("robe of the archmagi", [
    ItemEffect(AC_BONUS_UNARMORED, 5, requires_attunement=True),
    ItemEffect(SAVE_BONUS, 1, requires_attunement=True),
    ItemEffect(SPELL_SAVE_DC, 2, requires_attunement=True),
])
_register("scarab of protection", [
    ItemEffect(SAVE_BONUS, 1, requires_attunement=True),
])
_register("robe of stars", [
    ItemEffect(SAVE_BONUS, 1, requires_attunement=True),
])
_register("stone of good luck", [
    ItemEffect(SAVE_BONUS, 1, requires_attunement=True),
    ItemEffect(ABILITY_CHECK_BONUS, 1, requires_attunement=True),
])
_register("ioun stone, mastery", [
    ItemEffect(SAVE_BONUS, 0, requires_attunement=True),
])
_register("ioun stone, protection", [
    ItemEffect(AC_BONUS, 1, requires_attunement=True),
])
_register("mantle of spell resistance", [
    ItemEffect(SAVE_BONUS, 0, requires_attunement=True),
])
_register("luck blade", [
    ItemEffect(SAVE_BONUS, 1, requires_attunement=True),
    ItemEffect(WEAPON_ATTACK_DAMAGE, 1, requires_attunement=True),
])

# ─── Ability Score Override Items ─────────────────────────────────────
_register("gauntlets of ogre power", [
    ItemEffect(ABILITY_SET, "Strength:19", requires_attunement=True),
])
_register("headband of intellect", [
    ItemEffect(ABILITY_SET, "Intelligence:19", requires_attunement=True),
])
_register("amulet of health", [
    ItemEffect(ABILITY_SET, "Constitution:19", requires_attunement=True),
])
_register("belt of hill giant strength", [
    ItemEffect(ABILITY_SET, "Strength:21", requires_attunement=True),
])
_register("belt of frost giant strength", [
    ItemEffect(ABILITY_SET, "Strength:23", requires_attunement=True),
])
_register("belt of stone giant strength", [
    ItemEffect(ABILITY_SET, "Strength:23", requires_attunement=True),
])
_register("belt of fire giant strength", [
    ItemEffect(ABILITY_SET, "Strength:25", requires_attunement=True),
])
_register("belt of cloud giant strength", [
    ItemEffect(ABILITY_SET, "Strength:27", requires_attunement=True),
])
_register("belt of storm giant strength", [
    ItemEffect(ABILITY_SET, "Strength:29", requires_attunement=True),
])
_register("ioun stone, strength", [
    ItemEffect(ABILITY_SET, "Strength:19", requires_attunement=True),
])
_register("ioun stone, agility", [
    ItemEffect(ABILITY_SET, "Dexterity:19", requires_attunement=True),
])
_register("ioun stone, fortitude", [
    ItemEffect(ABILITY_SET, "Constitution:19", requires_attunement=True),
])
_register("ioun stone, insight", [
    ItemEffect(ABILITY_SET, "Wisdom:19", requires_attunement=True),
])
_register("ioun stone, intellect", [
    ItemEffect(ABILITY_SET, "Intelligence:19", requires_attunement=True),
])
_register("ioun stone, leadership", [
    ItemEffect(ABILITY_SET, "Charisma:19", requires_attunement=True),
])

# ─── Ranged Damage Bonus ─────────────────────────────────────────────
_register("bracers of archery", [
    ItemEffect(DAMAGE_BONUS_RANGED, 2, requires_attunement=True),
])

# ─── Spell Focus Items ───────────────────────────────────────────────
_register("all-purpose tool, +1", [
    ItemEffect(SPELL_ATTACK, 1, requires_attunement=True),
    ItemEffect(SPELL_SAVE_DC, 1, requires_attunement=True),
])
_register("all-purpose tool, +2", [
    ItemEffect(SPELL_ATTACK, 2, requires_attunement=True),
    ItemEffect(SPELL_SAVE_DC, 2, requires_attunement=True),
])
_register("all-purpose tool, +3", [
    ItemEffect(SPELL_ATTACK, 3, requires_attunement=True),
    ItemEffect(SPELL_SAVE_DC, 3, requires_attunement=True),
])
_register("arcane grimoire, +1", [
    ItemEffect(SPELL_ATTACK, 1, requires_attunement=True),
    ItemEffect(SPELL_SAVE_DC, 1, requires_attunement=True),
])
_register("arcane grimoire, +2", [
    ItemEffect(SPELL_ATTACK, 2, requires_attunement=True),
    ItemEffect(SPELL_SAVE_DC, 2, requires_attunement=True),
])
_register("arcane grimoire, +3", [
    ItemEffect(SPELL_ATTACK, 3, requires_attunement=True),
    ItemEffect(SPELL_SAVE_DC, 3, requires_attunement=True),
])
_register("amulet of the devout, +1", [
    ItemEffect(SPELL_ATTACK, 1, requires_attunement=True),
    ItemEffect(SPELL_SAVE_DC, 1, requires_attunement=True),
])
_register("amulet of the devout, +2", [
    ItemEffect(SPELL_ATTACK, 2, requires_attunement=True),
    ItemEffect(SPELL_SAVE_DC, 2, requires_attunement=True),
])
_register("amulet of the devout, +3", [
    ItemEffect(SPELL_ATTACK, 3, requires_attunement=True),
    ItemEffect(SPELL_SAVE_DC, 3, requires_attunement=True),
])

# ─── Initiative Items ────────────────────────────────────────────────
_register("weapon of warning", [
    ItemEffect(INITIATIVE_BONUS, 0, requires_attunement=True),
])
_register("sentinel shield", [
    ItemEffect(INITIATIVE_BONUS, 0),
])

# ─── Other Notable Items ─────────────────────────────────────────────
_register("demon armor", [
    ItemEffect(AC_BONUS_ARMOR, 1, requires_attunement=True),
    ItemEffect(WEAPON_ATTACK_DAMAGE, 1, requires_attunement=True),
])

import re


# ─── Activation Logic ────────────────────────────────────────────────

# Pattern to strip variant suffix: "weapon, +2 (longsword)" → "weapon, +2"
_VARIANT_SUFFIX_RE = re.compile(r"\s*\([^)]+\)\s*$")


def _base_item_key(item_key: str) -> str:
    """Strip variant suffix from composite item key to get the effects registry key.

    E.g. "weapon, +2 (longsword)" → "weapon, +2"
         "flame tongue (greatsword)" → "flame tongue"
         "ring of protection" → "ring of protection" (unchanged)
    """
    base = _VARIANT_SUFFIX_RE.sub("", item_key).strip()
    return base


def _lookup_effects(item_key: str) -> list[ItemEffect]:
    """Look up effects for an item, trying both the full key and the base key."""
    effects = ITEM_EFFECTS.get(item_key)
    if effects is not None:
        return effects
    base = _base_item_key(item_key)
    if base != item_key:
        effects = ITEM_EFFECTS.get(base)
        if effects is not None:
            return effects
    return []

def _all_owned_item_keys(character) -> set[str]:
    """Return all item keys that the character owns (in any inventory slot)."""
    keys: set[str] = set()

    for item in getattr(character, "custom_inventory", []) or []:
        name = (item.get("name") or "").strip().lower()
        if name:
            keys.add(name)

    for key in getattr(character, "equipped_weapons", []) or []:
        keys.add(str(key).strip().lower())

    for key in getattr(character, "equipped_armor", []) or []:
        keys.add(str(key).strip().lower())

    for key in getattr(character, "equipped_gear", []) or []:
        keys.add(str(key).strip().lower())

    return keys


def _is_equipped_weapon(item_key: str, character) -> bool:
    equipped = set(str(k).lower() for k in (getattr(character, "equipped_weapons", []) or []))
    return item_key in equipped


def _is_equipped_armor(item_key: str, character) -> bool:
    equipped = set(str(k).lower() for k in (getattr(character, "equipped_armor", []) or []))
    return item_key in equipped


def _is_attuned(item_key: str, character) -> bool:
    attuned = set(str(k).lower() for k in (getattr(character, "attuned_items", []) or []))
    return item_key in attuned


def _item_category(item_key: str, character) -> str | None:
    """Determine what kind of item this is from inventory data."""
    for item in getattr(character, "custom_inventory", []) or []:
        name = (item.get("name") or "").strip().lower()
        if name == item_key:
            return (item.get("category") or "").strip()
    return None


def is_effect_active(
    item_key: str, character, effect: ItemEffect,
    *, check_weapon: str | None = None,
) -> bool:
    """Check if a specific item effect is currently active.

    For weapon-specific effects (WEAPON_ATTACK_DAMAGE, EXTRA_WEAPON_DAMAGE),
    also checks that the weapon is equipped.

    For armor/shield effects, checks the armor is equipped.
    For attunement effects, checks the item is attuned.
    For general effects, checks the item is owned.
    """
    item_key = item_key.lower()

    # Attunement gate — must be attuned if required.
    # Check both the full key and the base key (without variant suffix).
    if effect.requires_attunement:
        if not _is_attuned(item_key, character):
            base = _base_item_key(item_key)
            if base == item_key or not _is_attuned(base, character):
                return False

    etype = effect.effect_type

    # Weapon-specific effects require the weapon to be equipped
    if etype in (WEAPON_ATTACK_DAMAGE, EXTRA_WEAPON_DAMAGE):
        return _is_equipped_weapon(item_key, character)

    # Armor-specific effects require the armor to be equipped
    if etype in (AC_BONUS_ARMOR, AC_BONUS_SHIELD):
        return _is_equipped_armor(item_key, character)

    # Everything else: just needs to be owned (or attuned, already checked)
    owned = _all_owned_item_keys(character)
    if item_key in owned:
        return True
    base = _base_item_key(item_key)
    return base != item_key and base in owned


# ─── Query Helpers ────────────────────────────────────────────────────

def get_weapon_attack_bonus(character, weapon_key: str) -> int:
    """Get total magic attack bonus for a specific equipped weapon."""
    weapon_key = weapon_key.lower()
    bonus = 0
    effects = _lookup_effects(weapon_key)
    for eff in effects:
        if eff.effect_type == WEAPON_ATTACK_DAMAGE:
            if is_effect_active(weapon_key, character, eff):
                bonus += int(eff.value)
    return bonus


def get_weapon_damage_bonus(character, weapon_key: str) -> int:
    """Get total magic damage bonus for a specific equipped weapon."""
    return get_weapon_attack_bonus(character, weapon_key)


def get_weapon_extra_damage(character, weapon_key: str) -> list[str]:
    """Get extra damage dice strings for a specific weapon (e.g. '2d6 fire')."""
    weapon_key = weapon_key.lower()
    extras: list[str] = []
    effects = _lookup_effects(weapon_key)
    for eff in effects:
        if eff.effect_type == EXTRA_WEAPON_DAMAGE:
            if is_effect_active(weapon_key, character, eff):
                label = str(eff.value)
                if eff.condition:
                    label += f" ({eff.condition})"
                extras.append(label)
    return extras


def get_ranged_damage_bonus(character) -> int:
    """Get bonus damage for ranged weapon attacks (e.g. Bracers of Archery)."""
    bonus = 0
    for _key, eff in _iter_active_effects(character):
        if eff.effect_type == DAMAGE_BONUS_RANGED:
            bonus += int(eff.value)
    return bonus


def _iter_active_effects(character) -> list[tuple[str, ItemEffect]]:
    """Yield (item_key, effect) for all active effects on the character.

    Handles variant suffixed keys by checking the base name in the registry.
    """
    results: list[tuple[str, ItemEffect]] = []
    seen_keys: set[str] = set()

    # Direct registry scan — covers items stored with their exact registry name
    for item_key, effects in ITEM_EFFECTS.items():
        for eff in effects:
            if is_effect_active(item_key, character, eff):
                results.append((item_key, eff))
                seen_keys.add(item_key)

    # Also scan owned items for variant-suffixed names not in the registry
    for owned_key in _all_owned_item_keys(character):
        if owned_key in seen_keys or owned_key in ITEM_EFFECTS:
            continue
        base = _base_item_key(owned_key)
        if base != owned_key and base in ITEM_EFFECTS:
            for eff in ITEM_EFFECTS[base]:
                if is_effect_active(owned_key, character, eff):
                    results.append((owned_key, eff))

    return results


def get_active_ac_bonus(character) -> int:
    """Get total general AC bonus from all active items (Ring of Protection, etc.)."""
    bonus = 0
    for _key, eff in _iter_active_effects(character):
        if eff.effect_type == AC_BONUS:
            bonus += int(eff.value)
    return bonus


def get_armor_ac_bonus(character, armor_key: str) -> int:
    """Get magic AC bonus for a specific equipped armor piece."""
    armor_key = armor_key.lower()
    bonus = 0
    effects = _lookup_effects(armor_key)
    for eff in effects:
        if eff.effect_type == AC_BONUS_ARMOR:
            if is_effect_active(armor_key, character, eff):
                bonus += int(eff.value)
    return bonus


def get_shield_ac_bonus(character, shield_key: str) -> int:
    """Get magic AC bonus for a specific equipped shield."""
    shield_key = shield_key.lower()
    bonus = 0
    effects = _lookup_effects(shield_key)
    for eff in effects:
        if eff.effect_type == AC_BONUS_SHIELD:
            if is_effect_active(shield_key, character, eff):
                bonus += int(eff.value)
    return bonus


def get_unarmored_ac_bonus(character) -> int:
    """Get AC bonus that only applies when not wearing armor (Bracers of Defense, etc.)."""
    bonus = 0
    for _key, eff in _iter_active_effects(character):
        if eff.effect_type == AC_BONUS_UNARMORED:
            bonus += int(eff.value)
    return bonus


def get_spell_attack_bonus(character) -> int:
    """Get bonus to spell attack rolls from focus items."""
    bonus = 0
    for _key, eff in _iter_active_effects(character):
        if eff.effect_type == SPELL_ATTACK:
            bonus = max(bonus, int(eff.value))
    return bonus


def get_spell_save_dc_bonus(character) -> int:
    """Get bonus to spell save DC from focus items."""
    bonus = 0
    for _key, eff in _iter_active_effects(character):
        if eff.effect_type == SPELL_SAVE_DC:
            bonus = max(bonus, int(eff.value))
    return bonus


def get_save_bonus(character) -> int:
    """Get total bonus to all saving throws from active items."""
    bonus = 0
    for _key, eff in _iter_active_effects(character):
        if eff.effect_type == SAVE_BONUS:
            bonus += int(eff.value)
    return bonus


def get_ability_check_bonus(character) -> int:
    """Get bonus to all ability checks (Stone of Good Luck, etc.)."""
    bonus = 0
    for _key, eff in _iter_active_effects(character):
        if eff.effect_type == ABILITY_CHECK_BONUS:
            bonus += int(eff.value)
    return bonus


def get_ability_overrides(character) -> dict[str, int]:
    """Get ability score overrides from active items.

    Returns {ability_name: min_value}. Multiple items for the same ability
    use the highest value.
    """
    overrides: dict[str, int] = {}
    for _key, eff in _iter_active_effects(character):
        if eff.effect_type == ABILITY_SET:
            parts = str(eff.value).split(":")
            if len(parts) == 2:
                ability_name = parts[0]
                min_val = int(parts[1])
                overrides[ability_name] = max(
                    overrides.get(ability_name, 0), min_val
                )
    return overrides


def get_effective_ability_score(character, ability_name: str) -> int:
    """Get ability score for an ability, applying item overrides if higher."""
    base = character.ability_scores.total(ability_name)
    overrides = get_ability_overrides(character)
    override = overrides.get(ability_name, 0)
    return max(base, override)


def get_effective_modifier(character, ability_name: str) -> int:
    """Get ability modifier using effective (possibly overridden) score."""
    score = get_effective_ability_score(character, ability_name)
    return (score - 10) // 2
