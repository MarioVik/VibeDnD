"""Pure business logic for the level-up wizard.

No tkinter imports — all state lives in LevelUpContext and helper
functions return data that the UI layer can render.
"""

import json
import os
import re
from dataclasses import dataclass, field

from models.character import Character
from models.class_level import ClassLevel
from models.language_utils import STANDARD_LANGUAGES
from paths import data_dir

# ── Class choices data (maneuvers, invocations, plans, arcane shots) ──

_CHOICES_PATH = os.path.join(data_dir(), "class_choices.json")
try:
    with open(_CHOICES_PATH, encoding="utf-8") as _f:
        CLASS_CHOICES: dict = json.load(_f)
except Exception:
    CLASS_CHOICES = {}

SLOT_ORDER = {
    "1st": 1,
    "2nd": 2,
    "3rd": 3,
    "4th": 4,
    "5th": 5,
    "6th": 6,
    "7th": 7,
    "8th": 8,
    "9th": 9,
}

SWAP_CLASSES = {"bard", "sorcerer", "warlock"}

ALL_ABILITIES = [
    "Strength",
    "Dexterity",
    "Constitution",
    "Intelligence",
    "Wisdom",
    "Charisma",
]

DAMAGE_TYPES = [
    "Acid",
    "Cold",
    "Fire",
    "Force",
    "Lightning",
    "Necrotic",
    "Poison",
    "Psychic",
    "Radiant",
    "Thunder",
]

_AMMO_NAMES = {"Arrows", "Bolts", "Bullets, Firearm", "Bullets, Sling", "Needles"}
_SWORD_NAMES = {"Greatsword", "Longsword", "Rapier", "Scimitar", "Shortsword"}


# ── Context dataclass ─────────────────────────────────────────────────


@dataclass
class LevelUpContext:
    """Mutable state for a level-up in progress."""

    # Determined at init
    new_total_level: int = 0
    primary_class_slug: str = ""

    # Class being levelled
    class_slug: str = ""
    new_class_level: int = 1

    # HP
    hp_mode: str = "average"  # "average" | "manual"
    hp_manual_value: str = ""

    # Subclass
    subclass_slug: str | None = None
    subclass_name: str = ""

    # Feat / ASI
    feat_name: str = ""
    asi_selections: dict[str, int] = field(default_factory=dict)
    asi_mode: str = "+2 to one ability"
    asi_ability1: str = ""
    asi_ability2: str = ""
    asi_choice: str = ""

    # Spells
    selected_new_cantrips: list[str] = field(default_factory=list)
    selected_new_spells: list[str] = field(default_factory=list)

    # Spell swap
    swap_out_cantrip: str | None = None
    swap_in_cantrip: str | None = None
    swap_out_spell: str | None = None
    swap_in_spell: str | None = None

    # Class choices (maneuvers, invocations, etc.)
    selected_new_choices: set[str] = field(default_factory=set)
    choice_sub_selections: dict[str, str] = field(default_factory=dict)
    replace_out: str = ""
    replace_in: str = ""

    # Proficiency/expertise grants
    prof_picks: list[str] = field(default_factory=list)
    expertise_picks: list[str] = field(default_factory=list)

    # Deft Explorer language picks
    language_selections: list[str] = field(default_factory=list)


# ── Data helpers ──────────────────────────────────────────────────────


def _to_int(v) -> int:
    if not v:
        return 0
    if isinstance(v, int):
        return v
    s = str(v).strip()
    if not s or s == "-":
        return 0
    try:
        return int(s.replace("+", ""))
    except Exception:
        return 0


def spell_deltas(
    class_slug: str, new_class_level: int, game_data
) -> tuple[int, int, int]:
    """Return (new_cantrip_count, new_prepared_count, max_spell_level)."""
    level_data = game_data.get_level_data(class_slug, new_class_level)
    if not level_data:
        return 0, 0, 0
    prev = game_data.get_level_data(class_slug, new_class_level - 1)
    if not prev:
        return 0, 0, 0

    curr_cantrips = _to_int(level_data.get("cantrips"))
    prev_cantrips = _to_int(prev.get("cantrips"))
    curr_prepared = _to_int(level_data.get("prepared_spells"))
    prev_prepared = _to_int(prev.get("prepared_spells"))

    curr_slots = level_data.get("spell_slots") or {}
    max_spell_level = max((SLOT_ORDER.get(k, 0) for k in curr_slots), default=0)
    pact_level = _to_int(level_data.get("pact_slot_level"))
    if pact_level > max_spell_level:
        max_spell_level = pact_level

    return (
        max(curr_cantrips - prev_cantrips, 0),
        max(curr_prepared - prev_prepared, 0),
        max_spell_level,
    )


def has_new_spell_options(class_slug: str, new_class_level: int, game_data) -> bool:
    new_cantrips, new_prepared, _ = spell_deltas(class_slug, new_class_level, game_data)
    return new_cantrips > 0 or new_prepared > 0


def has_language_step(class_slug: str, new_class_level: int, game_data) -> bool:
    level_data = game_data.get_level_data(class_slug, new_class_level)
    if not level_data:
        return False
    return "Deft Explorer" in level_data.get("features", [])


def can_swap(class_slug: str, character: Character) -> tuple[bool, bool]:
    """Return (can_swap_cantrips, can_swap_spells)."""
    if class_slug not in SWAP_CLASSES:
        return False, False
    has_cantrips = len(character.selected_cantrips) > 0
    has_spells = len(character.selected_spells) > 0
    return has_cantrips, has_spells


def has_swap_step(class_slug: str, character: Character) -> bool:
    can_c, can_s = can_swap(class_slug, character)
    return can_c or can_s


def get_current_subclass(
    ctx: LevelUpContext, character: Character, game_data
) -> str | None:
    """Return the subclass slug for the class being levelled."""
    if ctx.subclass_slug:
        return ctx.subclass_slug
    if ctx.subclass_name:
        name = ctx.subclass_name.replace(" (PHB)", "")
        for sc in game_data.get_subclasses_for_class(ctx.class_slug):
            if sc["name"] == name:
                return sc["slug"]
    for cl in character.class_levels:
        if cl.class_slug == ctx.class_slug and cl.subclass_slug:
            return cl.subclass_slug
    return None


def get_choices_config(
    ctx: LevelUpContext, character: Character, game_data
) -> dict | None:
    level_str = str(ctx.new_class_level)
    cfg = CLASS_CHOICES.get(ctx.class_slug)
    if cfg and cfg.get("gains_by_level", {}).get(level_str):
        return cfg
    sub = get_current_subclass(ctx, character, game_data)
    if sub:
        cfg = CLASS_CHOICES.get(sub)
        if cfg and cfg.get("gains_by_level", {}).get(level_str):
            return cfg
    return None


def has_class_choices(ctx: LevelUpContext, character: Character, game_data) -> bool:
    return get_choices_config(ctx, character, game_data) is not None


def get_known_choices(character: Character, key: str) -> list[str]:
    result: list[str] = []
    for cl in character.class_levels:
        if cl.class_slug == key or cl.subclass_slug == key:
            result.extend(cl.new_choices)
            if cl.replaced_choice and cl.replaced_choice in result:
                result.remove(cl.replaced_choice)
    return result


def get_active_pool(config: dict, new_class_level: int) -> str | None:
    return config.get("pools", {}).get(str(new_class_level))


def get_available_options(
    config: dict, ctx: LevelUpContext, character: Character
) -> list[dict]:
    options = config.get("options", [])
    active_pool = get_active_pool(config, ctx.new_class_level)
    if active_pool:
        options = [o for o in options if o.get("pool") == active_pool]

    key = ctx.class_slug
    for k, v in CLASS_CHOICES.items():
        if v is config:
            key = k
            break
    known = set(get_known_choices(character, key))
    result = []
    for opt in options:
        name = opt["name"]
        if name in known:
            continue
        prereq = opt.get("prerequisite_level")
        if prereq and ctx.new_class_level < prereq:
            continue
        min_lvl = opt.get("min_level")
        if min_lvl and ctx.new_class_level < min_lvl:
            continue
        result.append(opt)
    return result


def get_sub_choice_options(sub_choice: dict, game_data) -> list[str]:
    sc_type = sub_choice.get("type", "")
    sc_filter = sub_choice.get("filter", "")
    if not game_data:
        return []

    if sc_type == "weapon":
        weapons = game_data.items_by_category.get("Weapons", [])
        if sc_filter == "all":
            return sorted(w["name"] for w in weapons if w["name"] not in _AMMO_NAMES)
        elif sc_filter == "ammunition":
            return sorted(
                w["name"]
                for w in weapons
                if w["name"] not in _AMMO_NAMES
                and "ammunition" in w.get("description", "").lower()
            )
        elif sc_filter == "thrown":
            return sorted(
                w["name"]
                for w in weapons
                if w["name"] not in _AMMO_NAMES
                and "thrown" in w.get("description", "").lower()
            )
        elif sc_filter == "sword":
            return sorted(_SWORD_NAMES)

    elif sc_type == "armor":
        armors = game_data.items_by_category.get("Armor", [])
        if sc_filter == "no_shield":
            return sorted(a["name"] for a in armors if a["name"] != "Shield")

    elif sc_type == "armor_and_damage_type":
        armors = game_data.items_by_category.get("Armor", [])
        return sorted(a["name"] for a in armors if a["name"] != "Shield")

    elif sc_type == "magic_item":
        magic = game_data.items_by_category.get("Magic Items", [])
        if sc_filter == "common":
            return sorted(
                m["name"]
                for m in magic
                if m.get("rarity") == "Common"
                and m.get("type") not in ("Potion", "Scroll")
            )
        elif sc_filter == "uncommon_wondrous":
            return sorted(
                m["name"]
                for m in magic
                if m.get("rarity") == "Uncommon" and m.get("type") == "Wondrous Item"
            )
        elif sc_filter == "rare_wondrous":
            return sorted(
                m["name"]
                for m in magic
                if m.get("rarity") == "Rare" and m.get("type") == "Wondrous Item"
            )

    return []


def get_subclass_grants(
    ctx: LevelUpContext, character: Character, game_data
) -> list[dict]:
    sub_slug = get_current_subclass(ctx, character, game_data)
    if not sub_slug:
        return []
    subclass = game_data.get_subclass(ctx.class_slug, sub_slug)
    if not subclass:
        return []
    feats = subclass.get("features", {}).get(str(ctx.new_class_level), [])
    grants = []
    for feat in feats:
        gp = feat.get("grants_proficiency")
        ge = feat.get("grants_expertise")
        if gp or ge:
            grants.append(
                {
                    "feature_name": feat["name"],
                    "grants_proficiency": gp,
                    "grants_expertise": ge,
                }
            )
    return grants


def has_proficiency_step(ctx: LevelUpContext, character: Character, game_data) -> bool:
    for g in get_subclass_grants(ctx, character, game_data):
        gp = g.get("grants_proficiency")
        ge = g.get("grants_expertise")
        if gp and not gp.get("automatic"):
            return True
        if ge and not ge.get("automatic") and not ge.get("from_granted"):
            return True
    return False


def level_grants_asi(level_data: dict | None) -> bool:
    if not level_data:
        return False
    features = level_data.get("features", [])
    return any("Ability Score Improvement" in f for f in features)


def level_grants_subclass(level_data: dict | None) -> bool:
    if not level_data:
        return False
    features = level_data.get("features", [])
    return any("Subclass" in f and "Feature" not in f for f in features)


def get_spell_summary(ctx: LevelUpContext, game_data) -> list[str]:
    """Return informational lines about spellcasting changes at this level."""
    level_data = game_data.get_level_data(ctx.class_slug, ctx.new_class_level)
    if not level_data:
        return []
    new_cantrips, new_prepared, _ = spell_deltas(
        ctx.class_slug, ctx.new_class_level, game_data
    )
    prev = game_data.get_level_data(ctx.class_slug, ctx.new_class_level - 1) or {}
    curr_slots = level_data.get("spell_slots", {})
    prev_slots = prev.get("spell_slots", {})
    new_slot_levels = set(curr_slots.keys()) - set(prev_slots.keys())

    parts = []
    if new_cantrips > 0:
        parts.append(f"Learn {new_cantrips} new cantrip(s)")
    if new_prepared > 0:
        parts.append(f"Prepare {new_prepared} additional spell(s)")

    # Per-level additional spell slots
    for k, v in sorted(curr_slots.items(), key=lambda x: SLOT_ORDER.get(x[0], 99)):
        prev_v = int(prev_slots.get(k, 0) or 0)
        diff = int(v) - prev_v
        if diff > 0:
            parts.append(
                f"+{diff} additional {k}-level spell slot{'s' if diff != 1 else ''}"
            )
        elif k in new_slot_levels:
            # New level unlocked but no increase shown yet
            parts.append(
                f"+{v} additional {k}-level spell slot{'s' if int(v) != 1 else ''}"
            )

    return parts


def parse_asi_options(feat: dict) -> list[str]:
    """Parse ability score increase options from feat benefit description."""
    for benefit in feat.get("benefits", []):
        if benefit.get("name", "") == "Ability Score Increase":
            desc = benefit.get("description", "")
            match = re.search(r"Increase your (.+?) scores?\b", desc)
            if match:
                raw = match.group(1)
                parts = re.split(r",\s*(?:or\s+)?|\s+or\s+", raw)
                options = [p.strip() for p in parts if p.strip() in ALL_ABILITIES]
                if options:
                    return options
    asi_field = feat.get("ability_score_increase")
    if asi_field and asi_field in ALL_ABILITIES:
        return [asi_field]
    return []


def get_max_swap_spell_level(ctx: LevelUpContext, game_data) -> int:
    """Return the max spell level available for swapping."""
    _, _, max_spell_level = spell_deltas(ctx.class_slug, ctx.new_class_level, game_data)
    if max_spell_level == 0:
        level_data = game_data.get_level_data(ctx.class_slug, ctx.new_class_level)
        if level_data:
            curr_slots = level_data.get("spell_slots") or {}
            max_spell_level = max((SLOT_ORDER.get(k, 0) for k in curr_slots), default=0)
            pact_lvl = level_data.get("pact_slot_level")
            if pact_lvl and isinstance(pact_lvl, int) and pact_lvl > max_spell_level:
                max_spell_level = pact_lvl
    return max_spell_level


# ── Validation ────────────────────────────────────────────────────────


def validate_class_step(
    ctx: LevelUpContext, character: Character
) -> tuple[bool, str, str]:
    if (
        ctx.class_slug != ctx.primary_class_slug
        and character.class_level_in(ctx.class_slug) == 0
    ):
        met, reason = character.multiclass_prereqs_met(ctx.class_slug)
        if not met:
            return (
                False,
                "Prerequisites Not Met",
                f"Cannot multiclass into {ctx.class_slug.title()}:\n{reason}",
            )
        pri_met, pri_reason = character.multiclass_prereqs_met(ctx.primary_class_slug)
        if not pri_met:
            return (
                False,
                "Prerequisites Not Met",
                f"Cannot multiclass out of {ctx.primary_class_slug.title()}:\n{pri_reason}",
            )
    return True, "", ""


def validate_features_step(ctx: LevelUpContext) -> tuple[bool, str, str]:
    """Validate HP selection (legacy — kept for backward compatibility)."""
    return validate_hp_step(ctx)


def validate_hp_step(ctx: LevelUpContext) -> tuple[bool, str, str]:
    """Validate HP selection."""
    if ctx.hp_mode == "manual":
        try:
            val = int(ctx.hp_manual_value.strip())
            if val < 1:
                raise ValueError
        except (ValueError, AttributeError):
            return (
                False,
                "Invalid HP",
                "Please enter a valid number (>= 1) for your hit points.",
            )
    return True, "", ""


def validate_subclass_step(ctx: LevelUpContext) -> tuple[bool, str, str]:
    if not ctx.subclass_name and not ctx.subclass_slug:
        return False, "Missing Choice", "Please select a subclass."
    return True, "", ""


def validate_asi_step(
    ctx: LevelUpContext, character: Character, game_data
) -> tuple[bool, str, str]:
    if not ctx.feat_name:
        return (
            False,
            "Missing Choice",
            "Please select a feat for your Ability Score Improvement.",
        )
    feat = game_data.find_feat(ctx.feat_name)
    asi_field = feat.get("ability_score_increase") if feat else None
    if ctx.feat_name == "Ability Score Improvement":
        if not ctx.asi_selections:
            return (
                False,
                "Missing Choice",
                "Please select which ability scores to increase.",
            )
        for ab, amt in ctx.asi_selections.items():
            if character.ability_scores.total(ab) + amt > 20:
                return (
                    False,
                    "Score Too High",
                    f"{ab} would exceed 20. Please choose a different ability.",
                )
    elif asi_field and not ctx.asi_selections:
        return False, "Missing Choice", "Please select which ability score to increase."
    return True, "", ""


def validate_proficiency_step(
    ctx: LevelUpContext, character: Character, game_data
) -> tuple[bool, str, str]:
    grants = get_subclass_grants(ctx, character, game_data)
    prof_needed = 0
    exp_needed = 0
    for g in grants:
        gp = g.get("grants_proficiency")
        ge = g.get("grants_expertise")
        if gp and not gp.get("automatic"):
            prof_needed += gp.get("count", 1)
        if ge and not ge.get("automatic") and not ge.get("from_granted"):
            exp_needed += ge.get("count", 1)
    if len(ctx.prof_picks) < prof_needed:
        return False, "Missing Choice", "Please select all skill proficiencies."
    if len(ctx.expertise_picks) < exp_needed:
        return False, "Missing Choice", "Please select all skill expertise choices."
    if len(ctx.prof_picks) != len(set(ctx.prof_picks)):
        return (
            False,
            "Duplicate Choice",
            "Please choose different skills for each proficiency.",
        )
    return True, "", ""


def validate_language_step(ctx: LevelUpContext) -> tuple[bool, str, str]:
    if len(ctx.language_selections) < 2:
        return (
            False,
            "Missing Choice",
            f"Deft Explorer grants 2 languages. Please choose ({len(ctx.language_selections)}/2 selected).",
        )
    return True, "", ""


def validate_choices_step(
    ctx: LevelUpContext, character: Character, game_data
) -> tuple[bool, str, str]:
    config = get_choices_config(ctx, character, game_data)
    if not config:
        return True, "", ""
    required = config.get("gains_by_level", {}).get(str(ctx.new_class_level), 0)
    label = config.get("choice_plural", "choices")
    if len(ctx.selected_new_choices) < required:
        return False, "Missing Choice", f"Please select {required} new {label}."
    out = ctx.replace_out
    inp = ctx.replace_in
    if out and not inp:
        return (
            False,
            "Incomplete Swap",
            f"You chose to remove a {config.get('choice_label', 'choice')} but haven't selected a replacement.",
        )

    # Build options-by-name lookup
    options_by_name = {o["name"]: o for o in config.get("options", [])}

    for name in ctx.selected_new_choices:
        opt = options_by_name.get(name)
        if not opt or "sub_choice" not in opt:
            continue
        sub_sel = ctx.choice_sub_selections.get(name, "")
        sc_type = opt["sub_choice"].get("type", "")
        if not sub_sel:
            return (
                False,
                "Missing Selection",
                f'"{name}" requires you to select a specific item.',
            )
        if sc_type == "armor_and_damage_type" and "|" not in sub_sel:
            return (
                False,
                "Missing Damage Type",
                f'"{name}" requires both an armor and a damage type selection.',
            )

    if inp:
        opt = options_by_name.get(inp)
        if opt and "sub_choice" in opt:
            sub_sel = ctx.choice_sub_selections.get(inp, "")
            sc_type = opt["sub_choice"].get("type", "")
            if not sub_sel:
                return (
                    False,
                    "Missing Selection",
                    f'Replacement "{inp}" requires you to select a specific item.',
                )
            if sc_type == "armor_and_damage_type" and "|" not in sub_sel:
                return (
                    False,
                    "Missing Damage Type",
                    f'Replacement "{inp}" requires both an armor and a damage type.',
                )
    return True, "", ""


def validate_spell_step(ctx: LevelUpContext, game_data) -> tuple[bool, str, str]:
    new_cantrips_max, new_prepared_max, _ = spell_deltas(
        ctx.class_slug, ctx.new_class_level, game_data
    )
    if new_cantrips_max > 0 and len(ctx.selected_new_cantrips) < new_cantrips_max:
        return (
            False,
            "Missing Choice",
            f"Please select {new_cantrips_max} new cantrip(s).",
        )
    if new_prepared_max > 0 and len(ctx.selected_new_spells) < new_prepared_max:
        return (
            False,
            "Missing Choice",
            f"Please select {new_prepared_max} new spell(s).",
        )
    return True, "", ""


def validate_swap_step(ctx: LevelUpContext) -> tuple[bool, str, str]:
    if ctx.swap_out_cantrip and not ctx.swap_in_cantrip:
        return (
            False,
            "Incomplete Swap",
            "You selected a cantrip to forget but didn't pick one to learn.",
        )
    if ctx.swap_out_spell and not ctx.swap_in_spell:
        return (
            False,
            "Incomplete Swap",
            "You selected a spell to forget but didn't pick one to learn.",
        )
    return True, "", ""


# ── Apply level-up ────────────────────────────────────────────────────


def build_class_level(
    ctx: LevelUpContext, character: Character, game_data
) -> ClassLevel:
    """Construct the ClassLevel from the completed context."""
    # Resolve HP
    selected_class_data = None
    for cls in game_data.classes:
        if cls.get("slug") == ctx.class_slug:
            selected_class_data = cls
            break

    hit_die = selected_class_data.get("hit_die", 8) if selected_class_data else 8

    if ctx.hp_mode == "manual":
        hp_roll = int(ctx.hp_manual_value.strip())
    else:
        hp_roll = hit_die // 2 + 1

    cl = ClassLevel(
        class_slug=ctx.class_slug,
        class_level=ctx.new_class_level,
        hp_roll=hp_roll,
        hit_die=hit_die,
    )

    # Subclass
    if ctx.subclass_slug:
        cl.subclass_slug = ctx.subclass_slug
    elif ctx.subclass_name:
        sub_name = ctx.subclass_name.replace(" (PHB)", "")
        for sc in game_data.get_subclasses_for_class(ctx.class_slug):
            if sc["name"] == sub_name:
                cl.subclass_slug = sc["slug"]
                break
        if not cl.subclass_slug:
            cl.subclass_slug = sub_name.lower().replace(" ", "-")

    # Feat / ASI
    if ctx.feat_name:
        cl.feat_choice = ctx.feat_name
        if ctx.asi_selections:
            cl.asi_increases = dict(ctx.asi_selections)
        else:
            feat = game_data.find_feat(ctx.feat_name)
            asi_field = feat.get("ability_score_increase") if feat else None
            if asi_field and asi_field != "Choice" and asi_field in ALL_ABILITIES:
                cl.asi_increases = {asi_field: 1}

    # Spells
    cl.new_cantrips = list(ctx.selected_new_cantrips)
    cl.new_spells = list(ctx.selected_new_spells)

    # Class choices
    if ctx.selected_new_choices:
        cl.new_choices = list(ctx.selected_new_choices)
    if ctx.replace_out and ctx.replace_in:
        cl.replaced_choice = ctx.replace_out
        cl.new_choices.append(ctx.replace_in)
    if ctx.choice_sub_selections:
        cl.choice_sub_selections = dict(ctx.choice_sub_selections)

    # Proficiency/expertise
    if ctx.prof_picks:
        cl.new_proficiencies = list(ctx.prof_picks)
        for g in get_subclass_grants(ctx, character, game_data):
            ge = g.get("grants_expertise")
            if ge and ge.get("from_granted"):
                cl.new_expertise = list(ctx.prof_picks)
    if ctx.expertise_picks:
        cl.new_expertise.extend(ctx.expertise_picks)

    # Automatic grants
    for g in get_subclass_grants(ctx, character, game_data):
        gp = g.get("grants_proficiency")
        ge = g.get("grants_expertise")
        if gp and gp.get("automatic"):
            for s in gp.get("skills", []):
                if s not in cl.new_proficiencies:
                    cl.new_proficiencies.append(s)
        if ge and ge.get("automatic"):
            for s in ge.get("skills", []):
                if s not in cl.new_expertise:
                    cl.new_expertise.append(s)

    # Swap
    if ctx.swap_out_cantrip and ctx.swap_in_cantrip:
        cl.swapped_out_cantrip = ctx.swap_out_cantrip
        cl.swapped_in_cantrip = ctx.swap_in_cantrip
    if ctx.swap_out_spell and ctx.swap_in_spell:
        cl.swapped_out_spell = ctx.swap_out_spell
        cl.swapped_in_spell = ctx.swap_in_spell

    return cl


def apply_level_up(character: Character, cl: ClassLevel, ctx: LevelUpContext):
    """Apply all mutations to the character."""
    # ASI
    for ability, amount in cl.asi_increases.items():
        current = character.ability_scores.total(ability)
        new_val = min(current + amount, 20)
        increase = new_val - current
        if increase > 0:
            old_base = character.ability_scores.base(ability)
            character.ability_scores.set_base(ability, old_base + increase)

    # Spells
    character.selected_cantrips.extend(ctx.selected_new_cantrips)
    character.selected_spells.extend(ctx.selected_new_spells)

    # Swaps
    if cl.swapped_out_cantrip and cl.swapped_in_cantrip:
        if cl.swapped_out_cantrip in character.selected_cantrips:
            character.selected_cantrips.remove(cl.swapped_out_cantrip)
        character.selected_cantrips.append(cl.swapped_in_cantrip)
    if cl.swapped_out_spell and cl.swapped_in_spell:
        if cl.swapped_out_spell in character.selected_spells:
            character.selected_spells.remove(cl.swapped_out_spell)
        character.selected_spells.append(cl.swapped_in_spell)

    # Languages
    for lang in ctx.language_selections:
        if lang not in character.chosen_languages:
            character.chosen_languages.append(lang)

    # Append the level
    character.class_levels.append(cl)


# ── Step visibility ───────────────────────────────────────────────────


def get_visible_step_keys(
    ctx: LevelUpContext, character: Character, game_data
) -> list[str]:
    """Return the ordered list of visible level-up step keys."""
    level_data = game_data.get_level_data(ctx.class_slug, ctx.new_class_level)
    keys = []

    # Multiclass step — show if character has at least 1 level already
    if character.level >= 1:
        keys.append("lu_class")

    # Hit Points — always
    keys.append("lu_hp")

    # Features — always
    keys.append("lu_features")

    # Subclass — if this level grants "Subclass" (not "Subclass Feature")
    if level_grants_subclass(level_data):
        keys.append("lu_subclass")

    # Feat / ASI
    if level_grants_asi(level_data):
        keys.append("lu_asi")

    # Proficiency/expertise
    if has_proficiency_step(ctx, character, game_data):
        keys.append("lu_proficiencies")

    # Languages (Deft Explorer)
    if has_language_step(ctx.class_slug, ctx.new_class_level, game_data):
        keys.append("lu_languages")

    # Class choices
    if has_class_choices(ctx, character, game_data):
        keys.append("lu_choices")

    # Spells
    if has_new_spell_options(ctx.class_slug, ctx.new_class_level, game_data):
        keys.append("lu_spells")

    # Spell swap
    if has_swap_step(ctx.class_slug, character):
        keys.append("lu_swap")

    return keys
