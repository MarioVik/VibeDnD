"""Adapter between VibeDnD's models and the TUI.

The TUI never touches `models.Character` directly. `from_model()` builds
a flat, render-ready `CharacterView` snapshot using the model's real,
verified API (computed properties on `Character`, spellbook assembly via
`models.spell_grant_utils`, wealth via `models.inventory_service`,
equipment pools via `models.standard_actions`). Each section is built
defensively: a failing section degrades to its empty default instead of
crashing the app.

Write-backs (HP, spell slots) also live here — see `set_hp`,
`spend_slot`, `restore_slot` — and persist through
`models.character_store.save_character()` so saves stay readable by the
Tkinter GUI.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

ABILITIES = ("strength", "dexterity", "constitution",
             "intelligence", "wisdom", "charisma")

SKILL_ABILITY = {
    "Acrobatics": "dexterity", "Animal Handling": "wisdom",
    "Arcana": "intelligence", "Athletics": "strength",
    "Deception": "charisma", "History": "intelligence",
    "Insight": "wisdom", "Intimidation": "charisma",
    "Investigation": "intelligence", "Medicine": "wisdom",
    "Nature": "intelligence", "Perception": "wisdom",
    "Performance": "charisma", "Persuasion": "charisma",
    "Religion": "intelligence", "Sleight of Hand": "dexterity",
    "Stealth": "dexterity", "Survival": "wisdom",
}

# Slot-table keys are ordinals ("1st".."9th") in VibeDnD's data; pact
# magic is tracked separately on the model, so it gets its own key.
PACT_KEY = "Pact"

_ORDINAL = {1: "1st", 2: "2nd", 3: "3rd"}


def slot_key_for_level(level: int) -> str:
    """Spell level (1-9) -> slot-table key ("1st".."9th")."""
    return _ORDINAL.get(level, f"{level}th")


def mod(score: int | None) -> int | None:
    """D&D ability modifier."""
    if score is None:
        return None
    return (score - 10) // 2


def fmt_mod(value: int | None) -> str:
    if value is None:
        return "—"
    return f"+{value}" if value >= 0 else str(value)


@dataclass
class SpellView:
    name: str = "Unknown spell"
    level: int = 0
    school: str = ""
    casting_time: str = ""
    range: str = ""
    concentration: bool = False
    ritual: bool = False
    description: str = ""
    prepared: bool = False


@dataclass
class ItemView:
    name: str = "Unknown item"
    category: str = ""
    quantity: int = 1
    cost_cp: int | None = None
    description: str = ""


@dataclass
class FeatureView:
    name: str = ""
    source: str = ""          # e.g. "Fighter 1", "Species", "Feat"
    description: str = ""
    uses_max: int | None = None
    uses_left: int | None = None


@dataclass
class AttackView:
    name: str = ""
    attack: str = ""          # e.g. "+5"
    damage: str = ""          # e.g. "1d6+2 piercing"
    range: str = ""
    notes: str = ""           # weapon properties / mastery


@dataclass
class CharacterView:
    """Flat, render-ready snapshot of a character."""

    name: str = "Unnamed"
    species: str = "—"
    background: str = "—"
    class_line: str = "—"          # e.g. "Ranger 3 / Rogue 1"
    level: int = 1
    max_hp: int = 1
    current_hp: int = 1
    armor_class: Any = "—"
    speed: Any = "—"
    proficiency_bonus: int = 2
    abilities: dict[str, int | None] = field(default_factory=dict)
    skill_profs: set[str] = field(default_factory=set)
    expertise: set[str] = field(default_factory=set)
    save_profs: set[str] = field(default_factory=set)
    skill_mods: dict[str, int] = field(default_factory=dict)
    save_mods: dict[str, int] = field(default_factory=dict)
    spells: list[SpellView] = field(default_factory=list)
    spell_slots: dict[str, int] = field(default_factory=dict)
    spell_slots_used: dict[str, int] = field(default_factory=dict)
    inventory: list[ItemView] = field(default_factory=list)
    wealth: Any = "—"
    features: list[FeatureView] = field(default_factory=list)
    is_caster: bool = False
    # page-1 extras
    initiative: int | None = None
    size: str = "—"
    senses: list[str] = field(default_factory=list)
    hit_dice: dict[str, tuple[int, int, int]] = field(default_factory=dict)
    # ^ class slug -> (remaining, total, die size)
    temp_hp: int = 0
    attacks: list[AttackView] = field(default_factory=list)
    armor_training: list[str] = field(default_factory=list)
    weapon_training: list[str] = field(default_factory=list)
    tool_training: list[str] = field(default_factory=list)
    languages: list[str] = field(default_factory=list)
    coins: tuple[int, int, int] | None = None      # (gp, sp, cp)
    source_path: str | None = None  # save file, for write-backs
    raw: Any = None                 # underlying models.Character, if any

    @property
    def passive_perception(self) -> int | None:
        perception = self.skill_mod("Perception")
        return None if perception is None else 10 + perception

    @property
    def hp_fraction(self) -> float:
        if not self.max_hp:
            return 0.0
        return max(0.0, min(1.0, self.current_hp / self.max_hp))

    def skill_mod(self, skill: str) -> int | None:
        if skill in self.skill_mods:      # model-computed (item bonuses etc.)
            return self.skill_mods[skill]
        ability = SKILL_ABILITY.get(skill)
        base = mod(self.abilities.get(ability)) if ability else None
        if base is None:
            return None
        if skill in self.expertise:
            return base + 2 * self.proficiency_bonus
        if skill in self.skill_profs:
            return base + self.proficiency_bonus
        return base

    def save_mod(self, ability: str) -> int | None:
        title = ability.title()
        if title in self.save_mods:       # model-computed
            return self.save_mods[title]
        base = mod(self.abilities.get(ability.lower()))
        if base is None:
            return None
        return base + self.proficiency_bonus if title in self.save_profs else base


# --------------------------------------------------------------- builders --

def _class_line(c: Any) -> str:
    """Build 'Ranger 3 / Rogue 1' from Character.class_levels."""
    counts: dict[str, int] = {}
    for cl in c.class_levels or []:
        slug = str(cl.class_slug or "?")
        counts[slug] = counts.get(slug, 0) + 1
    if not counts:
        return f"{c.class_name} 1" if c.character_class else "—"
    return " / ".join(f"{slug.title()} {n}" for slug, n in counts.items())


def _spell_description(entry: dict) -> str:
    spell = entry.get("spell") or {}
    parts = [str(spell.get("description", "") or "").strip()]
    higher = str(spell.get("higher_levels") or "").strip()
    if higher:
        parts.append(f"At higher levels: {higher}")
    upgrade = str(spell.get("cantrip_upgrade") or "").strip()
    if upgrade:
        parts.append(f"Cantrip upgrade: {upgrade}")
    labels = [s for s in entry.get("source_labels", []) if s]
    if labels:
        parts.append(f"Granted by: {', '.join(labels)}")
    for note in entry.get("detail_notes", []) or []:
        parts.append(str(note))
    for fc in entry.get("free_casts", []) or []:
        parts.append(f"Free cast: {fc}")
    return "\n\n".join(p for p in parts if p)


def _spells(c: Any, gd: Any) -> list[SpellView]:
    from models.spell_grant_utils import get_spellbook_entries

    out = []
    for entry in get_spellbook_entries(c, gd):
        spell = entry.get("spell") or {}
        out.append(SpellView(
            name=str(entry.get("spell_name", "") or "Unknown spell"),
            level=int(entry.get("level", 0) or 0),
            school=str(spell.get("school", "") or ""),
            casting_time=str(spell.get("casting_time", "") or ""),
            range=str(spell.get("range", "") or ""),
            concentration=bool(spell.get("concentration")),
            ritual=bool(spell.get("ritual") or entry.get("ritual_only")),
            description=_spell_description(entry),
            prepared=bool(entry.get("base_selected")),
        ))
    return out


def _slots(c: Any, gd: Any) -> tuple[dict[str, int], dict[str, int]]:
    slots = {str(k): int(v) for k, v in (c.current_spell_slots(gd) or {}).items()
             if int(v) > 0}
    used = {k: min(int(c.used_spell_slots.get(k, 0) or 0), total)
            for k, total in slots.items()}
    pact_slots, _pact_level = c.current_pact_magic(gd)
    if pact_slots > 0:
        slots[PACT_KEY] = int(pact_slots)
        used[PACT_KEY] = min(int(c.used_pact_slots or 0), int(pact_slots))
    return slots, used


def _parse_qty(line: str) -> tuple[str, int]:
    """'10 Rations' -> ('Rations', 10); plain names default to qty 1."""
    parts = str(line).strip().split(None, 1)
    if len(parts) == 2 and parts[0].isdigit():
        return parts[1].strip(), max(1, int(parts[0]))
    return str(line).strip(), 1


def _lookup_key(name: str) -> str:
    """Lookup key tolerant of case and curly apostrophes."""
    return str(name).lower().replace("’", "'").replace("‘", "'")


def _display_name(name: str) -> str:
    """Title-case all-lowercase pool keys; keep mixed-case names as-is."""
    import string
    return string.capwords(name) if name == name.lower() else name


def _inventory(c: Any, gd: Any) -> list[ItemView]:
    from models.inventory_service import normalize_item_key
    from models.standard_actions import (get_selected_armor_counts,
                                         get_selected_non_weapon_items,
                                         get_selected_weapon_counts)

    # key -> [display name, qty, default category], insertion-ordered
    pools: dict[str, list] = {}

    def _add(name: str, qty: int, category: str) -> None:
        key = normalize_item_key(name)
        if not key or qty <= 0:
            return
        if key in pools:
            pools[key][1] += qty
        else:
            pools[key] = [name, qty, category]

    for key, n in (get_selected_weapon_counts(c) or {}).items():
        _add(key, int(n), "Weapons")
    for key, n in (get_selected_armor_counts(c) or {}).items():
        _add(key, int(n), "Armor")
    for line in get_selected_non_weapon_items(c) or []:
        name, qty = _parse_qty(line)
        _add(name, qty, "Adventuring Gear")
    for ent in c.custom_inventory or []:
        name = str(ent.get("name", "")).strip()
        if name:
            _add(name, max(1, int(ent.get("qty", 1) or 1)),
                 str(ent.get("category", "Adventuring Gear")))

    for raw_key, removed in (c.removed_items or {}).items():
        key = normalize_item_key(raw_key)
        if key in pools:
            pools[key][1] -= int(removed)

    by_name = {}
    for item_name, item in gd.items_by_name.items():
        by_name.setdefault(_lookup_key(item_name), item)
        if ", " in item_name:  # "Clothes, Traveler's" -> "traveler's clothes"
            head, _, tail = item_name.partition(", ")
            by_name.setdefault(_lookup_key(f"{tail} {head}"), item)

    out = []
    for key, (name, qty, category) in pools.items():
        if qty <= 0:
            continue
        bare = _lookup_key(name).split("(")[0].strip()  # drop "(3 days' worth)"
        item = (by_name.get(_lookup_key(key)) or by_name.get(_lookup_key(name))
                or by_name.get(bare) or {})
        out.append(ItemView(
            name=str(item.get("name") or _display_name(str(name))),
            category=str(item.get("category") or category),
            quantity=qty,
            cost_cp=item.get("cost_cp"),
            description=str(item.get("description", "") or ""),
        ))
    return out


def _feat_text(feat: dict | None) -> str:
    if not feat:
        return ""
    benefits = feat.get("benefits") or []
    lines = [f"{b.get('name', '')}: {b.get('description', '')}".strip(": ")
             for b in benefits if isinstance(b, dict)]
    return "\n\n".join(line for line in lines if line)


def _features(c: Any, gd: Any) -> list[FeatureView]:
    from gui.species_trait_utils import get_species_trait_cards  # tk-free

    out: list[FeatureView] = []

    if c.species:
        for trait in get_species_trait_cards(c.species):
            desc = str(trait.get("description", "") or "")
            for sub in trait.get("subtraits", []) or []:
                sub_desc = f"{sub.get('name', '')}: {sub.get('description', '')}"
                desc = f"{desc}\n\n{sub_desc}".strip()
            out.append(FeatureView(str(trait.get("name", "")), "Species", desc))

    if c.feat:
        out.append(FeatureView(f"Feat: {c.feat.get('name', '')}",
                               "Background", _feat_text(c.feat)))
    if c.species_origin_feat:
        out.append(FeatureView(f"Feat: {c.species_origin_feat.get('name', '')}",
                               "Species", _feat_text(c.species_origin_feat)))

    multiclass = len({cl.class_slug for cl in c.class_levels or []}) > 1
    for cl in c.class_levels or []:
        prefix = f"{str(cl.class_slug).title()} " if multiclass else ""
        source = f"{prefix}Level {cl.class_level}"
        level_data = gd.get_level_data(cl.class_slug, cl.class_level) or {}
        details = [f for f in level_data.get("feature_details", [])
                   if isinstance(f, dict)
                   and f.get("name") not in ("-", "Ability Score Improvement")]
        if not details:
            details = [{"name": n, "description": ""}
                       for n in level_data.get("features", [])
                       if n not in ("-", "Ability Score Improvement")]
        for feat in details:
            out.append(FeatureView(str(feat.get("name", "")), source,
                                   str(feat.get("description", "") or "")))
        if cl.feat_choice:
            asi = ", ".join(f"{a} +{v}"
                            for a, v in (cl.asi_increases or {}).items())
            out.append(FeatureView(f"Feat: {cl.feat_choice}", source, asi))

    if c.current_subclass and c.character_class:
        primary_slug = str(c.character_class.get("slug", "") or "")
        sc = gd.get_subclass(primary_slug, c.current_subclass) or {}
        sub_name = str(sc.get("name")
                       or c.current_subclass.replace("-", " ").title())
        for lvl, feats in sorted(
                (sc.get("features") or {}).items(),
                key=lambda kv: int(kv[0]) if str(kv[0]).isdigit() else 99):
            if not str(lvl).isdigit() or int(lvl) > c.level:
                continue
            for feat in feats:
                out.append(FeatureView(str(feat.get("name", "")),
                                       f"{sub_name} {lvl}",
                                       str(feat.get("description", "") or "")))
    return out


def _wealth_text(c: Any) -> str:
    from models.inventory_service import current_wealth_cp, format_coins
    return format_coins(current_wealth_cp(c), compact=True)


def _coins(c: Any) -> tuple[int, int, int]:
    from models.inventory_service import cp_to_coins, current_wealth_cp
    return cp_to_coins(current_wealth_cp(c))


def _attacks(c: Any, gd: Any) -> list[AttackView]:
    from models.standard_actions import build_standard_actions
    spells_by_name = {s.get("name", ""): s for s in gd.spells}
    rows = build_standard_actions(
        c, spells_by_name, game_data=gd,
        weapon_options=c.standard_action_options or {})
    return [AttackView(
        name=str(r.get("name", "") or ""),
        attack=str(r.get("attack", "") or ""),
        damage=str(r.get("damage", "") or ""),
        range="" if r.get("range") in (None, "-") else str(r.get("range")),
        notes=str(r.get("notes", "") or ""),
    ) for r in rows]


_SENSE_KEYWORDS = ("Darkvision", "Blindsight", "Tremorsense", "Truesight",
                   "Superior Darkvision", "Keen Senses", "Camouflage")


def _senses(c: Any) -> list[str]:
    """Mirror the PDF export's species-trait sense extraction."""
    import re
    traits = ((c.species or {}).get("features")
              or (c.species or {}).get("traits") or [])
    senses = []
    for trait in traits:
        name = str(trait.get("name", "") or "")
        if not any(kw in name for kw in _SENSE_KEYWORDS):
            continue
        match = re.search(r"(\d+)\s*feet", str(trait.get("description", "")))
        if match and "Darkvision" in name:
            senses.append(f"Darkvision {match.group(1)} ft")
        elif match and ("Blindsight" in name or "Tremorsense" in name):
            senses.append(f"{name} {match.group(1)} ft")
        else:
            senses.append(name)
    return senses


def _tools(c: Any) -> list[str]:
    """Background + class tool proficiencies, as on the PDF sheet."""
    tools = []
    background_tool = (c.background or {}).get("tool_proficiency")
    if background_tool:
        tools.append(str(background_tool))
    for tool in (c.character_class or {}).get("tool_proficiencies", []) or []:
        if tool not in tools:
            tools.append(str(tool))
    return tools


def _languages(c: Any) -> list[str]:
    from models.language_utils import all_languages
    return all_languages(c)


def from_model(character: Any, game_data: Any,
               source_path: str | None = None) -> CharacterView:
    """Build a CharacterView from a loaded `models.Character`."""
    c = character
    view = CharacterView(source_path=source_path, raw=c)

    def section(name: str, build, default):
        try:
            return build()
        except Exception as exc:                      # degrade, don't crash
            print(f"adapter: {name} failed for {getattr(c, 'name', '?')}: {exc}")
            return default

    view.name = section("name", lambda: str(c.name), "Unnamed")
    view.species = section("species", lambda: c.species_name, "—")
    view.background = section("background", lambda: c.background_name, "—")
    view.class_line = section("class_line", lambda: _class_line(c), "—")
    view.level = section("level", lambda: int(c.level), 1)
    view.max_hp = section("max_hp", lambda: max(1, int(c.hit_points)), 1)
    view.current_hp = section("current_hp",
                              lambda: max(0, int(c.effective_current_hp)),
                              view.max_hp)
    view.armor_class = section("armor_class", lambda: int(c.armor_class), "—")
    view.speed = section("speed", lambda: f"{int(c.speed)} ft.", "—")
    view.proficiency_bonus = section("proficiency_bonus",
                                     lambda: int(c.proficiency_bonus), 2)
    view.abilities = section(
        "abilities",
        lambda: {a: int(c.ability_scores.total(a.title())) for a in ABILITIES},
        {a: None for a in ABILITIES})
    view.skill_profs = section("skill_profs",
                               lambda: set(c.all_skill_proficiencies), set())
    view.expertise = section("expertise",
                             lambda: set(c.all_skill_expertise), set())
    view.skill_mods = section(
        "skill_mods",
        lambda: {s: int(c.skill_modifier(s)) for s in SKILL_ABILITY}, {})
    view.save_profs = section(
        "save_profs",
        lambda: {a.title() for a in ABILITIES if c.is_proficient_save(a.title())},
        set())
    view.save_mods = section(
        "save_mods",
        lambda: {a.title(): int(c.saving_throw_modifier(a.title()))
                 for a in ABILITIES}, {})
    view.spells = section("spells", lambda: _spells(c, game_data), [])
    view.spell_slots, view.spell_slots_used = section(
        "spell_slots", lambda: _slots(c, game_data), ({}, {}))
    view.inventory = section("inventory", lambda: _inventory(c, game_data), [])
    view.wealth = section("wealth", lambda: _wealth_text(c), "—")
    view.features = section("features", lambda: _features(c, game_data), [])
    view.is_caster = section("is_caster",
                             lambda: bool(c.is_caster) or bool(view.spells),
                             bool(view.spells))
    view.initiative = section("initiative", lambda: int(c.initiative), None)
    view.size = section("size", lambda: str(c.size_choice or "—"), "—")
    view.senses = section("senses", lambda: _senses(c), [])
    view.hit_dice = section("hit_dice", lambda: dict(c.hit_dice_pool), {})
    view.temp_hp = section("temp_hp", lambda: int(c.temp_hit_points or 0), 0)
    view.attacks = section("attacks", lambda: _attacks(c, game_data), [])
    view.armor_training = section(
        "armor_training", lambda: list(c.effective_armor_proficiencies), [])
    view.weapon_training = section(
        "weapon_training", lambda: list(c.effective_weapon_proficiencies), [])
    view.tool_training = section("tool_training", lambda: _tools(c), [])
    view.languages = section("languages", lambda: _languages(c), [])
    view.coins = section("coins", lambda: _coins(c), None)
    return view


# ------------------------------------------------------------ write-backs --

def persist(view: CharacterView) -> bool:
    """Save the underlying model back to its file (GUI-compatible format).

    Returns True unless an actual save attempt failed. Demo characters
    (no model / no file) are in-memory only and count as success.
    """
    if view.raw is None or not view.source_path:
        return True
    try:
        from paths import characters_dir
        from models.character_store import save_character
        save_character(view.raw, characters_dir(),
                       existing_filename=view.source_path)
        return True
    except Exception as exc:
        print(f"adapter: save failed for {view.name}: {exc}")
        return False


def set_hp(view: CharacterView, delta: int) -> bool:
    """Apply an HP change to the view and model, then persist."""
    view.current_hp = max(0, min(view.max_hp, view.current_hp + delta))
    if view.raw is not None:
        view.raw.current_hit_points = int(view.current_hp)
    return persist(view)


def _model_spend(c: Any, key: str, delta: int) -> None:
    """Mirror a slot change onto the model (key is a view slot key)."""
    model_key = "pact" if key == PACT_KEY else key
    if delta > 0:
        c.use_spell_slot(model_key)
    else:
        c.recover_spell_slots(model_key, -delta)


def spend_slot(view: CharacterView, key: str) -> bool:
    """Spend one spell slot of `key`. False if none left / unknown key."""
    total = view.spell_slots.get(key)
    used = view.spell_slots_used.get(key, 0)
    if total is None or used >= total:
        return False
    view.spell_slots_used[key] = used + 1
    if view.raw is not None:
        _model_spend(view.raw, key, +1)
    return persist(view)


def restore_slot(view: CharacterView, key: str) -> bool:
    """Restore one spent spell slot of `key`. False if none spent."""
    used = view.spell_slots_used.get(key, 0)
    if key not in view.spell_slots or used <= 0:
        return False
    view.spell_slots_used[key] = used - 1
    if view.raw is not None:
        _model_spend(view.raw, key, -1)
    return persist(view)


def adjust_wealth(view: CharacterView, delta_cp: int) -> tuple[bool, str]:
    """Add/subtract coins (in cp) via wealth_adjust_cp, GUI-style.

    Refuses reductions below zero, like the Tkinter wealth editor.
    Returns (ok, message for the user).
    """
    from .money import fmt_cp

    delta_cp = int(delta_cp)
    gp, sp, cp = view.coins or (0, 0, 0)
    current = gp * 100 + sp * 10 + cp
    if current + delta_cp < 0:
        return False, "Not enough wealth for that reduction"

    c = view.raw
    if c is not None:
        c.wealth_adjust_cp = int(c.wealth_adjust_cp or 0) + delta_cp
        if not persist(view):
            c.wealth_adjust_cp -= delta_cp
            return False, "Could not save the wealth change"
        view.wealth = _wealth_text(c)
        view.coins = _coins(c)
    else:                                   # demo: in-memory only
        total = current + delta_cp
        view.coins = (total // 100, total % 100 // 10, total % 10)
        view.wealth = fmt_cp(total)
    return True, f"Pouch: {fmt_cp(current + delta_cp)}"
