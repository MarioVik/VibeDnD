"""BDD step definitions for level 2→3 level-up tests."""
from __future__ import annotations

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from gui.data_loader import GameData
from gui.sheet_builder import get_level_feature_history, get_subclass_feature_sections
from models.character import Character
from models.class_level import ClassLevel
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
    has_language_step,
    validate_class_step,
    validate_hp_step,
    validate_subclass_step,
    validate_spell_step,
    validate_swap_step,
    validate_choices_step,
)

# ── Wire feature files ──────────────────────────────────────────────────────

scenarios("features/levelup3_step_visibility.feature")
scenarios("features/levelup3_features_display.feature")
scenarios("features/levelup3_subclass.feature")
scenarios("features/levelup3_spells.feature")
scenarios("features/levelup3_choices.feature")
scenarios("features/levelup3_swap.feature")
scenarios("features/levelup3_validation.feature")
scenarios("features/levelup3_apply.feature")
scenarios("features/levelup3_subclass_matrix.feature")

# ── Shared fixtures ─────────────────────────────────────────────────────────


@pytest.fixture(scope="session")
def game_data() -> GameData:
    return GameData()


# ── Helpers ─────────────────────────────────────────────────────────────────

_CLASS_SLUGS = {
    "Artificer": "artificer", "Barbarian": "barbarian", "Bard": "bard",
    "Cleric": "cleric", "Druid": "druid", "Fighter": "fighter",
    "Monk": "monk", "Paladin": "paladin", "Ranger": "ranger",
    "Rogue": "rogue", "Sorcerer": "sorcerer", "Warlock": "warlock",
    "Wizard": "wizard",
}

_HIT_DICE = {
    "artificer": 8, "barbarian": 12, "bard": 8, "cleric": 8,
    "druid": 8, "fighter": 10, "monk": 8, "paladin": 10,
    "ranger": 10, "rogue": 8, "sorcerer": 6, "warlock": 8, "wizard": 6,
}

_SUBCLASS_SLUGS = {
    "Battle Master": "battle-master",
    "Arcane Archer": "arcane-archer2",
    "Champion": "champion",
    "Tattooed Warrior": "tattooed-warrior2",
    "Hunter": "hunter",
}


def _build_level2_character(game_data: GameData, class_name: str) -> Character:
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
        ClassLevel(class_slug=slug, class_level=1, hit_die=hit_die),
        ClassLevel(class_slug=slug, class_level=2, hit_die=hit_die, hp_roll=hit_die // 2 + 1),
    ]
    return character


def _build_lu_ctx3(character: Character) -> LevelUpContext:
    slug = character.class_levels[0].class_slug
    return LevelUpContext(
        new_total_level=3,
        primary_class_slug=slug,
        class_slug=slug,
        new_class_level=3,
    )


def _pick_first_subclass(game_data: GameData, slug: str, ctx: LevelUpContext):
    subs = game_data.get_subclasses_for_class(slug)
    assert subs, f"No subclasses for {slug}"
    ctx.subclass_slug = subs[0]["slug"]
    ctx.subclass_name = subs[0]["name"]


def _fill_required_spells3(ctx, gd):
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


def _fill_required_choices3(ctx, char, gd):
    config = get_choices_config(ctx, char, gd)
    if config:
        required = config.get("gains_by_level", {}).get(str(ctx.new_class_level), 0)
        options = get_available_options(config, ctx, char)
        assert len(options) >= required, (
            f"Need {required} choice option(s) for {ctx.class_slug}/{ctx.subclass_slug}, "
            f"got {len(options)}"
        )
        selected = options[:required]
        ctx.selected_new_choices = {o["name"] for o in selected}
        for opt in selected:
            sub_choice = opt.get("sub_choice")
            if not sub_choice:
                continue
            sub_options = get_sub_choice_options(sub_choice, gd)
            assert sub_options, f"No sub-choice options for {opt['name']}"
            if sub_choice.get("type") == "armor_and_damage_type":
                ctx.choice_sub_selections[opt["name"]] = f"{sub_options[0]}|{DAMAGE_TYPES[0]}"
            else:
                ctx.choice_sub_selections[opt["name"]] = sub_options[0]


def _class_name_for_slug(game_data: GameData, class_slug: str) -> str:
    for cls in game_data.classes:
        if cls.get("slug") == class_slug:
            return cls["name"]
    raise AssertionError(f"Unknown class slug: {class_slug}")


def _apply_level3_subclass_case(game_data: GameData, subclass: dict) -> dict:
    class_name = _class_name_for_slug(game_data, subclass["class_slug"])
    character = _build_level2_character(game_data, class_name)
    ctx = _build_lu_ctx3(character)
    ctx.subclass_slug = subclass["slug"]
    ctx.subclass_name = subclass["name"]
    ctx.hp_mode = "average"

    _fill_required_spells3(ctx, game_data)
    _fill_required_choices3(ctx, character, game_data)

    choice_config = get_choices_config(ctx, character, game_data)
    if choice_config:
        ok, title, message = validate_choices_step(ctx, character, game_data)
        assert ok, f"{subclass['name']} choices invalid: {title} {message}".strip()

    cl = build_class_level(ctx, character, game_data)
    apply_level_up(character, cl, ctx, game_data)

    return {
        "class_name": class_name,
        "class_slug": subclass["class_slug"],
        "subclass": subclass,
        "character": character,
        "ctx": ctx,
        "class_level": character.class_levels[-1],
        "choice_config": choice_config,
        "selected_choices": set(ctx.selected_new_choices),
        "sheet_history": get_level_feature_history(character, game_data),
        "sheet_subclass": get_subclass_feature_sections(character, game_data),
    }


def _all_level3_subclass_cases(game_data: GameData) -> list[dict]:
    subclasses = sorted(
        game_data.subclasses,
        key=lambda sc: (sc.get("class_slug", ""), sc.get("name", "")),
    )
    return [_apply_level3_subclass_case(game_data, subclass) for subclass in subclasses]


# ── GIVEN ───────────────────────────────────────────────────────────────────


@given(
    parsers.parse("a level-2 {class_name} character ready to level up to 3"),
    target_fixture="lu3",
)
def given_level2_character(game_data: GameData, class_name: str):
    character = _build_level2_character(game_data, class_name)
    ctx = _build_lu_ctx3(character)
    return {"character": character, "ctx": ctx, "game_data": game_data}


@given("the level-3 character has existing spells")
def given_l3_has_spells(lu3):
    lu3["character"].selected_spells = ["Cure Wounds"]
    lu3["character"].selected_cantrips = ["Light"]


@given(parsers.parse("the {subclass_name} subclass is selected"))
def given_subclass_selected(lu3, subclass_name: str):
    slug = _SUBCLASS_SLUGS.get(subclass_name)
    assert slug, f"Unknown subclass: {subclass_name}"
    lu3["ctx"].subclass_slug = slug
    lu3["ctx"].subclass_name = subclass_name


@given("the full level-3 subclass matrix", target_fixture="subclass_matrix")
def given_full_level3_subclass_matrix(game_data: GameData):
    return {"game_data": game_data, "cases": []}


# ── WHEN: Step visibility ───────────────────────────────────────────────────


@when("the level-3 visible steps are computed", target_fixture="visible_steps3")
def when_visible_steps3(lu3):
    return get_visible_step_keys(lu3["ctx"], lu3["character"], lu3["game_data"])


# ── WHEN: Subclass ──────────────────────────────────────────────────────────


@when("no subclass is selected")
def when_no_subclass(lu3):
    lu3["ctx"].subclass_slug = None
    lu3["ctx"].subclass_name = ""


@when("a subclass is selected")
def when_subclass_selected(lu3):
    _pick_first_subclass(lu3["game_data"], lu3["ctx"].class_slug, lu3["ctx"])


# ── WHEN: Validation ────────────────────────────────────────────────────────


@when("no level-3 spells are selected")
def when_no_l3_spells(lu3):
    lu3["ctx"].selected_new_spells = []
    lu3["ctx"].selected_new_cantrips = []


@when("the required level-3 spells are selected")
def when_required_l3_spells(lu3):
    _fill_required_spells3(lu3["ctx"], lu3["game_data"])


# ── WHEN: Apply ─────────────────────────────────────────────────────────────


@when("the level-3 up is completed with defaults")
def when_l3_defaults(lu3):
    ctx = lu3["ctx"]
    gd = lu3["game_data"]
    char = lu3["character"]
    ctx.hp_mode = "average"
    if not ctx.subclass_slug:
        _pick_first_subclass(gd, ctx.class_slug, ctx)
    _fill_required_spells3(ctx, gd)
    _fill_required_choices3(ctx, char, gd)
    cl = build_class_level(ctx, char, gd)
    apply_level_up(char, cl, ctx, gd)


@when("the level-3 up is completed with a new spell")
def when_l3_with_spell(lu3):
    ctx = lu3["ctx"]
    gd = lu3["game_data"]
    char = lu3["character"]
    ctx.hp_mode = "average"
    if not ctx.subclass_slug:
        _pick_first_subclass(gd, ctx.class_slug, ctx)
    _fill_required_spells3(ctx, gd)
    lu3["_new_spell"] = ctx.selected_new_spells[0] if ctx.selected_new_spells else None
    cl = build_class_level(ctx, char, gd)
    apply_level_up(char, cl, ctx, gd)


@when("the level-3 up is completed with subclass choices")
def when_l3_with_subclass_choices(lu3):
    ctx = lu3["ctx"]
    gd = lu3["game_data"]
    char = lu3["character"]
    ctx.hp_mode = "average"
    _fill_required_spells3(ctx, gd)
    _fill_required_choices3(ctx, char, gd)
    cl = build_class_level(ctx, char, gd)
    apply_level_up(char, cl, ctx, gd)


@when("each subclass is applied at level 3 with valid defaults")
def when_each_subclass_applied(subclass_matrix):
    subclass_matrix["cases"] = _all_level3_subclass_cases(subclass_matrix["game_data"])


@when("each subclass with level-3 choices is applied using valid subclass choices")
def when_each_choice_subclass_applied(subclass_matrix):
    all_cases = _all_level3_subclass_cases(subclass_matrix["game_data"])
    subclass_matrix["cases"] = [
        case for case in all_cases if case["choice_config"] is not None
    ]


# ── THEN: Step visibility ──────────────────────────────────────────────────


@then(parsers.parse("the level-3 visible steps include {step_key}"))
def then_l3_includes(visible_steps3, step_key: str):
    assert step_key in visible_steps3, f"Expected {step_key} in {visible_steps3}"


@then(parsers.parse("the level-3 visible steps do not include {step_key}"))
def then_l3_excludes(visible_steps3, step_key: str):
    assert step_key not in visible_steps3, f"Unexpected {step_key} in {visible_steps3}"


# ── THEN: Features display ─────────────────────────────────────────────────


@then(parsers.parse("the level 3 features include {feature_name}"))
def then_l3_features_include(lu3, feature_name: str):
    gd = lu3["game_data"]
    ctx = lu3["ctx"]
    level_data = gd.get_level_data(ctx.class_slug, 3)
    assert level_data, f"No level 3 data for {ctx.class_slug}"
    features = level_data.get("features", [])
    assert feature_name in features, f"'{feature_name}' not in {features}"


# ── THEN: Subclass ──────────────────────────────────────────────────────────


@then(parsers.parse("at least one subclass is available for {class_name}"))
def then_subclass_available(lu3, class_name: str):
    slug = _CLASS_SLUGS[class_name]
    subs = lu3["game_data"].get_subclasses_for_class(slug)
    assert subs, f"No subclasses for {class_name}"


@then("the subclass step is invalid")
def then_subclass_invalid(lu3):
    ok, _, _ = validate_subclass_step(lu3["ctx"])
    assert not ok


@then("the subclass step is valid")
def then_subclass_valid(lu3):
    ok, _, _ = validate_subclass_step(lu3["ctx"])
    assert ok


# ── THEN: Spells ────────────────────────────────────────────────────────────


@then(parsers.parse("the level-3 new cantrip count is {expected:d}"))
def then_l3_cantrips(lu3, expected: int):
    ctx = lu3["ctx"]
    gd = lu3["game_data"]
    nc, _, _ = spell_deltas(ctx.class_slug, ctx.new_class_level, gd)
    assert nc == expected, f"Expected {expected} cantrips, got {nc}"


@then(parsers.parse("the level-3 new prepared spell count is {expected:d}"))
def then_l3_prepared(lu3, expected: int):
    ctx = lu3["ctx"]
    gd = lu3["game_data"]
    _, np_, _ = spell_deltas(ctx.class_slug, ctx.new_class_level, gd)
    assert np_ == expected, f"Expected {expected} prepared, got {np_}"


# ── THEN: Choices ───────────────────────────────────────────────────────────


@then(parsers.parse("the subclass class choices gain count at level 3 is {expected:d}"))
def then_subclass_choices_count(lu3, expected: int):
    ctx = lu3["ctx"]
    gd = lu3["game_data"]
    char = lu3["character"]
    config = get_choices_config(ctx, char, gd)
    assert config, "No choices config"
    gains = config.get("gains_by_level", {}).get("3", 0)
    assert gains == expected, f"Expected {expected}, got {gains}"


@then("the subclass class choice options are not empty")
def then_subclass_options_not_empty(lu3):
    ctx = lu3["ctx"]
    gd = lu3["game_data"]
    char = lu3["character"]
    config = get_choices_config(ctx, char, gd)
    assert config, "No choices config"
    options = get_available_options(config, ctx, char)
    assert options, "Expected non-empty options"


@then("no subclass class choices config exists at level 3")
def then_no_subclass_choices(lu3):
    ctx = lu3["ctx"]
    gd = lu3["game_data"]
    char = lu3["character"]
    assert get_choices_config(ctx, char, gd) is None


# ── THEN: Swap ──────────────────────────────────────────────────────────────


@then("level-3 spell swap is available")
def then_l3_swap_available(lu3):
    assert has_swap_step(lu3["ctx"].class_slug, lu3["character"])


@then("level-3 spell swap is not available")
def then_l3_swap_not_available(lu3):
    assert not has_swap_step(lu3["ctx"].class_slug, lu3["character"])


# ── THEN: Validation ────────────────────────────────────────────────────────


@then("the level-3 class step is valid")
def then_l3_class_valid(lu3):
    ok, _, _ = validate_class_step(lu3["ctx"], lu3["character"])
    assert ok


@then("the level-3 spell step is invalid")
def then_l3_spell_invalid(lu3):
    ok, _, _ = validate_spell_step(lu3["ctx"], lu3["game_data"])
    assert not ok


@then("the level-3 spell step is valid")
def then_l3_spell_valid(lu3):
    ok, _, _ = validate_spell_step(lu3["ctx"], lu3["game_data"])
    assert ok


# ── THEN: Apply / Persistence ──────────────────────────────────────────────


@then("the character level is 3")
def then_level_3(lu3):
    assert lu3["character"].level == 3


@then("the character has 3 class levels")
def then_3_class_levels(lu3):
    assert len(lu3["character"].class_levels) == 3


@then("the level-3 class level has a subclass slug")
def then_subclass_recorded(lu3):
    cl = lu3["character"].class_levels[-1]
    assert cl.subclass_slug, f"subclass_slug is {cl.subclass_slug!r}"


@then("the level-3 class level has a non-null hp_roll")
def then_l3_hp_recorded(lu3):
    cl = lu3["character"].class_levels[-1]
    assert cl.hp_roll is not None, "hp_roll is None"


@then("the character selected spells include the level-3 new spell")
def then_l3_spell_persisted(lu3):
    new_spell = lu3.get("_new_spell")
    assert new_spell, "No new spell was recorded"
    assert new_spell in lu3["character"].selected_spells


@then("the level-3 class level has non-empty new_choices")
def then_l3_choices_recorded(lu3):
    cl = lu3["character"].class_levels[-1]
    assert cl.new_choices, "new_choices is empty"


@then("the level 3 progression data has feature_details")
def then_l3_progression_details(lu3):
    gd = lu3["game_data"]
    ctx = lu3["ctx"]
    level_data = gd.get_level_data(ctx.class_slug, 3)
    assert level_data, f"No level 3 data for {ctx.class_slug}"
    details = level_data.get("feature_details", [])
    assert details, f"No feature_details for {ctx.class_slug} level 3"


# ── THEN: Exhaustive subclass matrix ───────────────────────────────────────


@then(parsers.parse("the matrix contains {expected:d} level-3 subclasses"))
def then_subclass_matrix_count(subclass_matrix, expected: int):
    assert len(subclass_matrix["cases"]) == expected


@then("every subclass has level-3 features with names and descriptions")
def then_every_subclass_has_complete_level3_features(subclass_matrix):
    for case in subclass_matrix["cases"]:
        features = case["subclass"].get("features", {}).get("3", [])
        assert features, f"{case['subclass']['name']} has no level-3 features"
        for feat in features:
            assert feat.get("name"), f"{case['subclass']['name']} has a level-3 feature with no name"
            assert (feat.get("description") or "").strip(), (
                f"{case['subclass']['name']}::{feat.get('name', '<unnamed>')} "
                "has no description"
            )


@then("every subclass level-up records its subclass slug")
def then_every_subclass_level_up_records_slug(subclass_matrix):
    for case in subclass_matrix["cases"]:
        recorded = case["class_level"].subclass_slug
        expected = case["subclass"]["slug"]
        assert recorded == expected, (
            f"{case['subclass']['name']} recorded subclass slug {recorded!r}, "
            f"expected {expected!r}"
        )


@then("every level-3 subclass feature appears in the shared character sheet subclass section")
def then_every_subclass_feature_appears_in_sheet_section(subclass_matrix):
    for case in subclass_matrix["cases"]:
        section = case["sheet_subclass"]
        assert section, f"No subclass section for {case['subclass']['name']}"
        level_entry = next(
            (entry for entry in section["levels"] if entry["level"] == 3),
            None,
        )
        assert level_entry, f"No level-3 subclass section for {case['subclass']['name']}"

        expected = [
            (
                feat.get("name", ""),
                (feat.get("description") or "").strip(),
            )
            for feat in case["subclass"].get("features", {}).get("3", [])
        ]
        actual = [
            (
                feat.get("name", ""),
                (feat.get("description") or "").strip(),
            )
            for feat in level_entry["features"]
        ]
        assert actual == expected, (
            f"Subclass sheet mismatch for {case['subclass']['name']}\n"
            f"expected={expected}\nactual={actual}"
        )


@then(parsers.parse("exactly {expected:d} subclasses grant level-3 class choices"))
def then_exact_choice_subclass_count(subclass_matrix, expected: int):
    assert len(subclass_matrix["cases"]) == expected


@then("every level-3 subclass choice config can satisfy its required picks")
def then_every_choice_config_can_satisfy_required_picks(subclass_matrix):
    for case in subclass_matrix["cases"]:
        config = case["choice_config"]
        assert config, f"No choice config for {case['subclass']['name']}"
        required = config.get("gains_by_level", {}).get("3", 0)
        assert required > 0, f"{case['subclass']['name']} has no level-3 choice gain"
        assert len(case["selected_choices"]) == required, (
            f"{case['subclass']['name']} selected {len(case['selected_choices'])} "
            f"choice(s), expected {required}"
        )


@then("every selected level-3 subclass choice is persisted on the class level")
def then_every_selected_choice_is_persisted(subclass_matrix):
    for case in subclass_matrix["cases"]:
        recorded = set(case["class_level"].new_choices)
        assert recorded == case["selected_choices"], (
            f"{case['subclass']['name']} persisted {recorded}, "
            f"expected {case['selected_choices']}"
        )


@then("every selected level-3 subclass choice appears in the shared character sheet history")
def then_every_selected_choice_appears_in_sheet_history(subclass_matrix):
    for case in subclass_matrix["cases"]:
        displayed = {
            item.get("name", "")
            for entry in case["sheet_history"]
            for item in entry["items"]
        }
        for choice_name in case["selected_choices"]:
            assert any(
                item == choice_name or item.startswith(f"{choice_name} (")
                for item in displayed
            ), f"{case['subclass']['name']} choice {choice_name!r} missing from sheet history"
