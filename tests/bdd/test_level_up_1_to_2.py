"""BDD step definitions for level 1→2 level-up tests."""
from __future__ import annotations

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from gui.data_loader import GameData
from models.character import Character
from models.class_level import ClassLevel
from models.level1_class_rules import (
    WARLOCK_CLASS_FEATURE_FOLLOWUP_INVOCATIONS,
    get_warlock_invocation_binding_options,
)
from models.level_up_logic import (
    DAMAGE_TYPES,
    LevelUpContext,
    build_class_level,
    apply_level_up,
    get_visible_step_keys,
    spell_deltas,
    get_spell_summary,
    has_new_spell_options,
    has_class_choices,
    get_choices_config,
    get_available_options,
    get_sub_choice_options,
    has_swap_step,
    can_swap,
    has_language_step,
    level_grants_subclass,
    level_grants_asi,
    validate_class_step,
    validate_hp_step,
    validate_features_step,
    validate_spell_step,
    validate_swap_step,
    validate_language_step,
    validate_choices_step,
)

# ── Wire feature files ──────────────────────────────────────────────────────

scenarios("features/levelup_step_visibility.feature")
scenarios("features/levelup_features_display.feature")
scenarios("features/levelup_hp.feature")
scenarios("features/levelup_spells.feature")
scenarios("features/levelup_choices.feature")
scenarios("features/levelup_swap.feature")
scenarios("features/levelup_languages.feature")
scenarios("features/levelup_validation.feature")
scenarios("features/levelup_apply.feature")

# ── Shared fixtures ─────────────────────────────────────────────────────────


@pytest.fixture(scope="session")
def game_data() -> GameData:
    return GameData()


# ── Helpers ─────────────────────────────────────────────────────────────────

_CLASS_SLUGS = {
    "Artificer": "artificer",
    "Barbarian": "barbarian",
    "Bard": "bard",
    "Cleric": "cleric",
    "Druid": "druid",
    "Fighter": "fighter",
    "Monk": "monk",
    "Paladin": "paladin",
    "Ranger": "ranger",
    "Rogue": "rogue",
    "Sorcerer": "sorcerer",
    "Warlock": "warlock",
    "Wizard": "wizard",
}

_HIT_DICE = {
    "artificer": 8, "barbarian": 12, "bard": 8, "cleric": 8,
    "druid": 8, "fighter": 10, "monk": 8, "paladin": 10,
    "ranger": 10, "rogue": 8, "sorcerer": 6, "warlock": 8, "wizard": 6,
}


def _build_level1_character(game_data: GameData, class_name: str) -> Character:
    slug = _CLASS_SLUGS[class_name]
    cls = None
    for c in game_data.classes:
        if c.get("slug") == slug:
            cls = c
            break
    assert cls, f"Unknown class: {class_name}"
    character = Character(name=f"BDD {class_name}", character_class=cls)
    hit_die = _HIT_DICE[slug]
    character.class_levels = [
        ClassLevel(class_slug=slug, class_level=1, hit_die=hit_die)
    ]
    return character


def _build_lu_ctx(character: Character) -> LevelUpContext:
    slug = character.class_levels[0].class_slug
    return LevelUpContext(
        new_total_level=2,
        primary_class_slug=slug,
        class_slug=slug,
        new_class_level=2,
    )


def _fill_required_spells(ctx, gd):
    new_cantrips, new_prepared, max_level = spell_deltas(
        ctx.class_slug, ctx.new_class_level, gd
    )
    if new_cantrips > 0 or new_prepared > 0:
        class_name = ctx.class_slug.title()
        all_spells = [s for s in gd.spells if class_name in s.get("classes", [])]
        cantrips = [s["name"] for s in all_spells if s.get("level", 99) == 0]
        leveled = [s["name"] for s in all_spells if 0 < s.get("level", 99) <= max_level]
        ctx.selected_new_cantrips = cantrips[:new_cantrips]
        ctx.selected_new_spells = leveled[:new_prepared]


def _fill_required_choices(ctx, char, gd):
    config = get_choices_config(ctx, char, gd)
    if not config:
        return
    required = config.get("gains_by_level", {}).get(str(ctx.new_class_level), 0)
    options = get_available_options(config, ctx, char)
    selected = options[:required]
    ctx.selected_new_choices = {o["name"] for o in selected}
    for opt in selected:
        name = opt["name"]
        sub_choice = opt.get("sub_choice")
        if sub_choice:
            sub_options = get_sub_choice_options(sub_choice, gd)
            assert sub_options, f"No sub-choice options for {name}"
            if sub_choice.get("type") == "armor_and_damage_type":
                ctx.choice_sub_selections[name] = f"{sub_options[0]}|{DAMAGE_TYPES[0]}"
            else:
                ctx.choice_sub_selections[name] = sub_options[0]
        elif WARLOCK_CLASS_FEATURE_FOLLOWUP_INVOCATIONS.get(name) == "binding":
            bind_opts = get_warlock_invocation_binding_options(char, gd)
            if not bind_opts:
                cantrips = list(char.selected_cantrips or [])
                if "Eldritch Blast" not in cantrips:
                    char.selected_cantrips = cantrips + ["Eldritch Blast"]
                bind_opts = get_warlock_invocation_binding_options(char, gd)
            if bind_opts:
                ctx.choice_sub_selections[name] = bind_opts[0]


# ── GIVEN ───────────────────────────────────────────────────────────────────


@given(
    parsers.parse("a level-1 {class_name} character ready to level up"),
    target_fixture="lu_bundle",
)
def given_level1_character(game_data: GameData, class_name: str):
    character = _build_level1_character(game_data, class_name)
    ctx = _build_lu_ctx(character)
    return {"character": character, "ctx": ctx, "game_data": game_data}


@given("the character has existing spells")
def given_character_has_spells(lu_bundle):
    lu_bundle["character"].selected_spells = ["Cure Wounds"]
    lu_bundle["character"].selected_cantrips = ["Light"]


# ── WHEN: Step visibility ───────────────────────────────────────────────────


@when("the visible level-up steps are computed", target_fixture="visible_steps")
def when_visible_steps_computed(lu_bundle):
    return get_visible_step_keys(
        lu_bundle["ctx"], lu_bundle["character"], lu_bundle["game_data"]
    )


# ── WHEN: HP ────────────────────────────────────────────────────────────────


@when("HP mode is set to average")
def when_hp_average(lu_bundle):
    lu_bundle["ctx"].hp_mode = "average"


@when(parsers.parse("HP mode is set to manual with value {value}"))
def when_hp_manual(lu_bundle, value: str):
    lu_bundle["ctx"].hp_mode = "manual"
    lu_bundle["ctx"].hp_manual_value = value


@when("HP mode is set to manual with value")
def when_hp_manual_empty(lu_bundle):
    lu_bundle["ctx"].hp_mode = "manual"
    lu_bundle["ctx"].hp_manual_value = ""


# ── WHEN: Swap ──────────────────────────────────────────────────────────────


@when("a cantrip swap out is selected without a swap in")
def when_cantrip_swap_out_no_in(lu_bundle):
    lu_bundle["ctx"].swap_out_cantrip = "Light"
    lu_bundle["ctx"].swap_in_cantrip = None


@when("a spell swap out is selected without a swap in")
def when_spell_swap_out_no_in(lu_bundle):
    lu_bundle["ctx"].swap_out_spell = "Cure Wounds"
    lu_bundle["ctx"].swap_in_spell = None


# ── WHEN: Languages ─────────────────────────────────────────────────────────


@when(parsers.parse("{count:d} language is selected"))
def when_n_language_selected(lu_bundle, count: int):
    lu_bundle["ctx"].language_selections = ["Elvish"][:count]


@when(parsers.parse("{count:d} languages are selected"))
def when_n_languages_selected(lu_bundle, count: int):
    langs = ["Elvish", "Dwarvish", "Giant", "Goblin"]
    lu_bundle["ctx"].language_selections = langs[:count]


# ── WHEN: Validation ────────────────────────────────────────────────────────


@when("no new spells are selected")
def when_no_spells(lu_bundle):
    lu_bundle["ctx"].selected_new_spells = []
    lu_bundle["ctx"].selected_new_cantrips = []


@when("the required new spells are selected")
def when_required_spells(lu_bundle):
    _fill_required_spells(lu_bundle["ctx"], lu_bundle["game_data"])


@when("no class choices are selected")
def when_no_choices(lu_bundle):
    lu_bundle["ctx"].selected_new_choices = set()


@when("the required class choices are selected")
def when_required_choices(lu_bundle):
    _fill_required_choices(
        lu_bundle["ctx"], lu_bundle["character"], lu_bundle["game_data"]
    )


# ── WHEN: Apply ─────────────────────────────────────────────────────────────


@when("the level-up is completed with defaults")
def when_levelup_defaults(lu_bundle):
    ctx = lu_bundle["ctx"]
    gd = lu_bundle["game_data"]
    char = lu_bundle["character"]
    ctx.hp_mode = "average"
    _fill_required_spells(ctx, gd)
    _fill_required_choices(ctx, char, gd)
    if has_language_step(ctx.class_slug, ctx.new_class_level, gd):
        ctx.language_selections = ["Elvish", "Dwarvish"]
    cl = build_class_level(ctx, char, gd)
    apply_level_up(char, cl, ctx, gd)


@when("the level-up is completed with a new spell")
def when_levelup_with_spell(lu_bundle):
    ctx = lu_bundle["ctx"]
    gd = lu_bundle["game_data"]
    char = lu_bundle["character"]
    ctx.hp_mode = "average"
    _fill_required_spells(ctx, gd)
    lu_bundle["_new_spell"] = (
        ctx.selected_new_spells[0] if ctx.selected_new_spells else None
    )
    cl = build_class_level(ctx, char, gd)
    apply_level_up(char, cl, ctx, gd)


@when("the level-up is completed with class choices")
def when_levelup_with_choices(lu_bundle):
    ctx = lu_bundle["ctx"]
    gd = lu_bundle["game_data"]
    char = lu_bundle["character"]
    ctx.hp_mode = "average"
    _fill_required_spells(ctx, gd)
    _fill_required_choices(ctx, char, gd)
    cl = build_class_level(ctx, char, gd)
    apply_level_up(char, cl, ctx, gd)


@when("the level-up is completed with 2 languages")
def when_levelup_with_languages(lu_bundle):
    ctx = lu_bundle["ctx"]
    gd = lu_bundle["game_data"]
    char = lu_bundle["character"]
    ctx.hp_mode = "average"
    ctx.language_selections = ["Elvish", "Dwarvish"]
    _fill_required_spells(ctx, gd)
    cl = build_class_level(ctx, char, gd)
    apply_level_up(char, cl, ctx, gd)


# ── THEN: Step visibility ──────────────────────────────────────────────────


@then(parsers.parse("the visible steps include {step_key}"))
def then_visible_includes(visible_steps, step_key: str):
    assert step_key in visible_steps, f"Expected {step_key} in {visible_steps}"


@then(parsers.parse("the visible steps do not include {step_key}"))
def then_visible_excludes(visible_steps, step_key: str):
    assert step_key not in visible_steps, f"Unexpected {step_key} in {visible_steps}"


# ── THEN: Features display ─────────────────────────────────────────────────


@then(parsers.parse("the level 2 features include {feature_name}"))
def then_level2_features_include(lu_bundle, feature_name: str):
    gd = lu_bundle["game_data"]
    ctx = lu_bundle["ctx"]
    level_data = gd.get_level_data(ctx.class_slug, 2)
    assert level_data, f"No level 2 data for {ctx.class_slug}"
    features = level_data.get("features", [])
    assert feature_name in features, f"'{feature_name}' not in {features}"


@then(parsers.parse("the level 2 feature {feature_name} has a description"))
def then_feature_has_description(lu_bundle, feature_name: str):
    gd = lu_bundle["game_data"]
    ctx = lu_bundle["ctx"]
    level_data = gd.get_level_data(ctx.class_slug, 2)
    assert level_data, f"No level 2 data for {ctx.class_slug}"
    details = level_data.get("feature_details", [])
    found = None
    for d in details:
        if d.get("name") == feature_name or feature_name in d.get("name", ""):
            found = d
            break
    assert found, f"No detail for '{feature_name}'"
    assert found.get("description"), f"Empty description for '{feature_name}'"


@then("the features step is valid")
def then_features_step_valid(lu_bundle):
    ok, _, _ = validate_features_step(lu_bundle["ctx"])
    assert ok


# ── THEN: HP ────────────────────────────────────────────────────────────────


@then("the HP step is valid")
def then_hp_valid(lu_bundle):
    ok, _, _ = validate_hp_step(lu_bundle["ctx"])
    assert ok


@then("the HP step is invalid")
def then_hp_invalid(lu_bundle):
    ok, _, _ = validate_hp_step(lu_bundle["ctx"])
    assert not ok


@then(parsers.parse("the average HP gain is {expected_avg:d}"))
def then_average_hp(lu_bundle, expected_avg: int):
    slug = lu_bundle["ctx"].class_slug
    hit_die = _HIT_DICE[slug]
    average = hit_die // 2 + 1
    assert average == expected_avg, f"Expected {expected_avg}, got {average}"


# ── THEN: Spells ────────────────────────────────────────────────────────────


@then(parsers.parse("the new cantrip count is {expected:d}"))
def then_new_cantrip_count(lu_bundle, expected: int):
    ctx = lu_bundle["ctx"]
    gd = lu_bundle["game_data"]
    nc, _, _ = spell_deltas(ctx.class_slug, ctx.new_class_level, gd)
    assert nc == expected, f"Expected {expected} cantrips, got {nc}"


@then(parsers.parse("the new prepared spell count is {expected:d}"))
def then_new_prepared_count(lu_bundle, expected: int):
    ctx = lu_bundle["ctx"]
    gd = lu_bundle["game_data"]
    _, np_, _ = spell_deltas(ctx.class_slug, ctx.new_class_level, gd)
    assert np_ == expected, f"Expected {expected} prepared, got {np_}"


@then("the spell summary is not empty")
def then_spell_summary_not_empty(lu_bundle):
    parts = get_spell_summary(lu_bundle["ctx"], lu_bundle["game_data"])
    assert parts, "Expected non-empty spell summary"


@then("the spell summary is empty")
def then_spell_summary_empty(lu_bundle):
    parts = get_spell_summary(lu_bundle["ctx"], lu_bundle["game_data"])
    has_new = any("cantrip" in p.lower() or "additional spell" in p.lower() for p in parts)
    assert not has_new, f"Unexpected spell summary lines: {parts}"


# ── THEN: Choices ───────────────────────────────────────────────────────────


@then(parsers.parse("the class choices gain count at level 2 is {expected:d}"))
def then_choices_gain_count(lu_bundle, expected: int):
    ctx = lu_bundle["ctx"]
    gd = lu_bundle["game_data"]
    char = lu_bundle["character"]
    config = get_choices_config(ctx, char, gd)
    assert config, "No choices config"
    gains = config.get("gains_by_level", {}).get("2", 0)
    assert gains == expected, f"Expected {expected}, got {gains}"


@then("the available class choice options are not empty")
def then_choices_options_not_empty(lu_bundle):
    ctx = lu_bundle["ctx"]
    gd = lu_bundle["game_data"]
    char = lu_bundle["character"]
    config = get_choices_config(ctx, char, gd)
    assert config, "No choices config"
    options = get_available_options(config, ctx, char)
    assert options, "Expected non-empty options"


@then("no class choices config exists")
def then_no_choices_config(lu_bundle):
    ctx = lu_bundle["ctx"]
    gd = lu_bundle["game_data"]
    char = lu_bundle["character"]
    assert get_choices_config(ctx, char, gd) is None


# ── THEN: Swap ──────────────────────────────────────────────────────────────


@then("spell swap is available")
def then_swap_available(lu_bundle):
    assert has_swap_step(lu_bundle["ctx"].class_slug, lu_bundle["character"])


@then("spell swap is not available")
def then_swap_not_available(lu_bundle):
    assert not has_swap_step(lu_bundle["ctx"].class_slug, lu_bundle["character"])


@then("the swap step is valid")
def then_swap_valid(lu_bundle):
    ok, _, _ = validate_swap_step(lu_bundle["ctx"])
    assert ok


@then("the swap step is invalid")
def then_swap_invalid(lu_bundle):
    ok, _, _ = validate_swap_step(lu_bundle["ctx"])
    assert not ok


# ── THEN: Languages ─────────────────────────────────────────────────────────


@then("the language step is required")
def then_language_required(lu_bundle):
    ctx = lu_bundle["ctx"]
    gd = lu_bundle["game_data"]
    assert has_language_step(ctx.class_slug, ctx.new_class_level, gd)


@then("the language step is not required")
def then_language_not_required(lu_bundle):
    ctx = lu_bundle["ctx"]
    gd = lu_bundle["game_data"]
    assert not has_language_step(ctx.class_slug, ctx.new_class_level, gd)


@then("the language step is valid")
def then_language_valid(lu_bundle):
    ok, _, _ = validate_language_step(lu_bundle["ctx"])
    assert ok


@then("the language step is invalid")
def then_language_invalid(lu_bundle):
    ok, _, _ = validate_language_step(lu_bundle["ctx"])
    assert not ok


# ── THEN: Validation ────────────────────────────────────────────────────────


@then("the class step is valid")
def then_class_step_valid(lu_bundle):
    ok, _, _ = validate_class_step(lu_bundle["ctx"], lu_bundle["character"])
    assert ok


@then("the spell step is invalid")
def then_spell_step_invalid(lu_bundle):
    ok, _, _ = validate_spell_step(lu_bundle["ctx"], lu_bundle["game_data"])
    assert not ok


@then("the spell step is valid")
def then_spell_step_valid(lu_bundle):
    ok, _, _ = validate_spell_step(lu_bundle["ctx"], lu_bundle["game_data"])
    assert ok


@then("the choices step is invalid")
def then_choices_step_invalid(lu_bundle):
    ok, _, _ = validate_choices_step(
        lu_bundle["ctx"], lu_bundle["character"], lu_bundle["game_data"]
    )
    assert not ok


@then("the choices step is valid")
def then_choices_step_valid(lu_bundle):
    ok, _, _ = validate_choices_step(
        lu_bundle["ctx"], lu_bundle["character"], lu_bundle["game_data"]
    )
    assert ok


# ── THEN: Apply / Persistence ──────────────────────────────────────────────


@then("the character level is 2")
def then_character_level_2(lu_bundle):
    assert lu_bundle["character"].level == 2


@then("the character has 2 class levels")
def then_character_has_2_levels(lu_bundle):
    assert len(lu_bundle["character"].class_levels) == 2


@then("the new class level has a non-null hp_roll")
def then_hp_roll_recorded(lu_bundle):
    cl = lu_bundle["character"].class_levels[-1]
    assert cl.hp_roll is not None, "hp_roll is None"


@then("the character selected spells include the new spell")
def then_spells_include_new(lu_bundle):
    new_spell = lu_bundle.get("_new_spell")
    assert new_spell, "No new spell was recorded"
    assert new_spell in lu_bundle["character"].selected_spells


@then("the new class level has non-empty new_choices")
def then_choices_recorded(lu_bundle):
    cl = lu_bundle["character"].class_levels[-1]
    assert cl.new_choices, "new_choices is empty"


@then("the character chosen languages include the new languages")
def then_languages_recorded(lu_bundle):
    char = lu_bundle["character"]
    assert "Elvish" in char.chosen_languages
    assert "Dwarvish" in char.chosen_languages


@then("the level 2 progression data has feature_details")
def then_progression_has_details(lu_bundle):
    gd = lu_bundle["game_data"]
    ctx = lu_bundle["ctx"]
    level_data = gd.get_level_data(ctx.class_slug, 2)
    assert level_data, f"No level 2 data for {ctx.class_slug}"
    details = level_data.get("feature_details", [])
    assert details, f"No feature_details for {ctx.class_slug} level 2"
