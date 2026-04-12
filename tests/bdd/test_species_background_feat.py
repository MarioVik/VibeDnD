"""BDD step definitions for species, background, and feat creation tests."""
from __future__ import annotations

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from gui.data_loader import GameData
from gui.species_trait_utils import get_species_trait_cards
from models.ability_bonus_utils import apply_background_ability_bonuses
from models.character import Character
from models.feat_utils import get_owned_feat_names
from models.level1_class_rules import get_available_origin_feats

# ── Wire feature files ──────────────────────────────────────────────────────

scenarios("features/species_creation.feature")
scenarios("features/background_creation.feature")
scenarios("features/feat_creation.feature")

# ── Shared fixtures ─────────────────────────────────────────────────────────


@pytest.fixture(scope="session")
def game_data() -> GameData:
    return GameData()


# ── Helpers ─────────────────────────────────────────────────────────────────

# Species whose feature block includes a required "choose one" trait option,
# mirroring gui/step_species.py SpeciesStep.TRAIT_OPTION_CHOICES.
TRAIT_OPTION_CHOICES: dict[str, dict] = {
    "Gnome": {
        "label": "Gnomish Lineage",
        "options": ["Forest Gnome", "Rock Gnome"],
    },
    "Goliath": {
        "label": "Giant Ancestry",
        "options": [
            "Cloud's Jaunt (Cloud Giant)",
            "Fire's Burn (Fire Giant)",
            "Frost's Chill (Frost Giant)",
            "Hill's Tumble (Hill Giant)",
            "Stone's Endurance (Stone Giant)",
            "Storm's Thunder (Storm Giant)",
        ],
    },
    "Shifter": {
        "label": "Shifting Option",
        "options": ["Beasthide", "Longtooth", "Swiftstride", "Wildhunt"],
    },
}


def _species_requires_sub_choice(species: dict) -> bool:
    """Return True when the species requires a sub-choice to be valid."""
    if species.get("sub_choices"):
        return True
    return species.get("name", "") in TRAIT_OPTION_CHOICES


def _species_grants_origin_feat(species: dict) -> bool:
    """Mirror FeatStep._species_grants_origin_feat logic."""
    for trait in species.get("traits", []):
        if "origin feat" in trait.get("description", "").lower():
            return True
    return False


def _build_character_with_species(
    game_data: GameData,
    species_name: str,
    *,
    sub_choice: str | None = None,
) -> Character:
    species = game_data.species_by_name.get(species_name)
    assert species, f"Unknown species: {species_name}"
    c = Character(name=f"BDD {species_name}")
    c.species = species
    c.species_sub_choice = sub_choice
    size_data = species.get("size", {})
    size_opts = (
        size_data.get("options", ["Medium"])
        if isinstance(size_data, dict)
        else ["Medium"]
    )
    c.size_choice = size_opts[0]
    return c


def _build_character_with_background(
    game_data: GameData,
    bg_name: str,
) -> Character:
    bg = game_data.backgrounds_by_name.get(bg_name)
    assert bg, f"Unknown background: {bg_name}"
    c = Character(name=f"BDD {bg_name}")
    c.background = bg
    feat_name = bg.get("feat")
    if feat_name:
        c.feat = game_data.find_feat(feat_name)
    apply_background_ability_bonuses(c)
    return c


def _is_species_step_valid(character: Character) -> bool:
    """Replicate SpeciesStep.is_valid() without GUI."""
    if character.species is None:
        return False
    if _species_requires_sub_choice(character.species):
        if not (character.species_sub_choice or "").strip():
            return False
    return True


# ── SPECIES: Given ──────────────────────────────────────────────────────────


@given("the species catalog", target_fixture="species_catalog")
def given_species_catalog(game_data: GameData) -> list[dict]:
    return list(game_data.species)


@given(
    parsers.parse("a character with the species {species_name}"),
    target_fixture="character",
)
def given_character_with_species(game_data: GameData, species_name: str) -> Character:
    return _build_character_with_species(game_data, species_name)


# ── SPECIES: When ───────────────────────────────────────────────────────────


@when("no sub-choice has been made")
def when_no_sub_choice(character: Character):
    character.species_sub_choice = None


@when(
    parsers.parse("the sub-choice {sub_choice} is selected"),
)
def when_sub_choice_selected(character: Character, sub_choice: str):
    character.species_sub_choice = sub_choice


@when(
    parsers.parse("the species is changed to {species_name}"),
)
def when_species_changed(character: Character, game_data: GameData, species_name: str):
    species = game_data.species_by_name.get(species_name)
    assert species, f"Unknown species: {species_name}"
    character.species = species
    character.species_sub_choice = None
    character.species_origin_feat = None


# ── SPECIES: Then ───────────────────────────────────────────────────────────


@then(parsers.parse("the catalog contains {count:d} species"))
def then_species_catalog_count(species_catalog: list[dict], count: int):
    assert len(species_catalog) == count


@then("every species has at least one trait")
def then_every_species_has_traits(species_catalog: list[dict]):
    for sp in species_catalog:
        assert sp.get("traits"), f"{sp['name']} has no traits"


@then("the species step is invalid")
def then_species_step_invalid(character: Character):
    assert not _is_species_step_valid(character)


@then("the species step is valid")
def then_species_step_valid(character: Character):
    assert _is_species_step_valid(character)


@then(parsers.parse("the character size is {expected_size}"))
def then_character_size(character: Character, expected_size: str):
    assert character.size_choice == expected_size


@then("the species grants an origin feat")
def then_species_grants_origin_feat(character: Character):
    assert _species_grants_origin_feat(character.species)


@then("the species does not grant an origin feat")
def then_species_does_not_grant_origin_feat(character: Character):
    assert not _species_grants_origin_feat(character.species)


@then("the species trait cards are not empty")
def then_species_trait_cards_not_empty(character: Character):
    cards = get_species_trait_cards(character.species)
    assert cards, "Expected non-empty trait cards"


@then(parsers.parse("the trait cards exclude {excluded_trait}"))
def then_trait_cards_exclude(character: Character, excluded_trait: str):
    species_name = character.species.get("name", "")
    trait_choice = TRAIT_OPTION_CHOICES.get(species_name)
    excluded_names = set(trait_choice["options"]) if trait_choice else set()
    cards = get_species_trait_cards(character.species, excluded_names=excluded_names)
    card_names = {card["name"] for card in cards}
    assert excluded_trait not in card_names


@then(parsers.parse("the character speed is {expected_speed:d}"))
def then_character_speed(character: Character, expected_speed: int):
    assert character.speed == expected_speed


@then("the character has no species origin feat")
def then_no_species_origin_feat(character: Character):
    assert character.species_origin_feat is None


# ── BACKGROUND: Given ───────────────────────────────────────────────────────


@given("the background catalog", target_fixture="background_catalog")
def given_background_catalog(game_data: GameData) -> list[dict]:
    return list(game_data.backgrounds)


@given(
    parsers.parse("a character with the background {bg_name}"),
    target_fixture="character",
)
def given_character_with_background(game_data: GameData, bg_name: str) -> Character:
    return _build_character_with_background(game_data, bg_name)


# ── BACKGROUND: When ────────────────────────────────────────────────────────


@when(parsers.parse("ability bonus mode is set to {mode}"))
def when_ability_bonus_mode(character: Character, mode: str):
    character.ability_bonus_mode = mode
    apply_background_ability_bonuses(character)


@when(parsers.parse("the background is changed to {bg_name}"))
def when_background_changed(character: Character, game_data: GameData, bg_name: str):
    bg = game_data.backgrounds_by_name.get(bg_name)
    assert bg, f"Unknown background: {bg_name}"
    character.background = bg
    feat_name = bg.get("feat")
    character.feat = game_data.find_feat(feat_name) if feat_name else None
    apply_background_ability_bonuses(character)


# ── BACKGROUND: Then ────────────────────────────────────────────────────────


@then(parsers.parse("the catalog contains {count:d} backgrounds"))
def then_background_catalog_count(background_catalog: list[dict], count: int):
    assert len(background_catalog) == count


@then("every background has exactly 2 skill proficiencies")
def then_every_background_has_2_skills(background_catalog: list[dict]):
    for bg in background_catalog:
        skills = bg.get("skill_proficiencies", [])
        assert len(skills) == 2, f"{bg['name']} has {len(skills)} skills: {skills}"


@then("every background has a feat")
def then_every_background_has_feat(background_catalog: list[dict]):
    for bg in background_catalog:
        assert bg.get("feat"), f"{bg['name']} has no feat"


@then("every background has equipment options")
def then_every_background_has_equipment(background_catalog: list[dict]):
    for bg in background_catalog:
        assert bg.get("equipment"), f"{bg['name']} has no equipment options"


@then(parsers.parse("the character is proficient in {skill}"))
def then_character_proficient_in(character: Character, skill: str):
    assert skill in character.all_skill_proficiencies, (
        f"Expected {skill} in {character.all_skill_proficiencies}"
    )


@then(parsers.parse("the character background feat is {feat_name}"))
def then_background_feat_is(character: Character, feat_name: str):
    assert character.feat is not None, "No background feat set"
    assert character.feat.get("name") == feat_name


@then("the background feat has at least one benefit")
def then_background_feat_has_benefits(character: Character):
    assert character.feat is not None
    benefits = character.feat.get("benefits", [])
    assert benefits, "Background feat has no benefits"


@then("one ability has a +2 bonus")
def then_one_ability_has_plus2(character: Character):
    bonuses = dict(character.ability_scores.bonuses)
    plus2_count = sum(1 for v in bonuses.values() if v == 2)
    assert plus2_count == 1, f"Expected 1 ability with +2, got {plus2_count}: {bonuses}"


@then("one other ability has a +1 bonus")
def then_one_other_ability_has_plus1(character: Character):
    bonuses = dict(character.ability_scores.bonuses)
    plus1_count = sum(1 for v in bonuses.values() if v == 1)
    assert plus1_count == 1, f"Expected 1 ability with +1, got {plus1_count}: {bonuses}"


@then("three abilities each have a +1 bonus")
def then_three_abilities_have_plus1(character: Character):
    bonuses = dict(character.ability_scores.bonuses)
    plus1_count = sum(1 for v in bonuses.values() if v == 1)
    assert plus1_count == 3, f"Expected 3 abilities with +1, got {plus1_count}: {bonuses}"


@then("no ability has any bonus")
def then_no_ability_bonuses(character: Character):
    bonuses = dict(character.ability_scores.bonuses)
    non_zero = {k: v for k, v in bonuses.items() if v != 0}
    assert not non_zero, f"Expected no bonuses, got {non_zero}"


@then(parsers.parse("the owned feat names include {feat_name}"))
def then_owned_feat_names_include(character: Character, feat_name: str):
    owned = get_owned_feat_names(character)
    assert feat_name.casefold() in owned, f"Expected {feat_name} in {owned}"


# ── FEAT: Given ─────────────────────────────────────────────────────────────


@given("the origin feat catalog", target_fixture="origin_feat_catalog")
def given_origin_feat_catalog(game_data: GameData) -> list[dict]:
    return get_available_origin_feats(game_data)


@given(parsers.parse("the character has origin feat {feat_name}"))
def given_character_has_origin_feat(character: Character, game_data: GameData, feat_name: str):
    feat = game_data.find_feat(feat_name)
    assert feat, f"Unknown feat: {feat_name}"
    character.species_origin_feat = feat


@given(
    "a warlock character with Lessons of the First Ones",
    target_fixture="character",
)
def given_warlock_with_lessons(game_data: GameData) -> Character:
    from models.class_level import ClassLevel

    cls = None
    for c in game_data.classes:
        if c.get("slug") == "warlock":
            cls = c
            break
    assert cls, "Warlock class not found"
    character = Character(name="BDD Warlock", character_class=cls)
    character.class_levels = [
        ClassLevel(class_slug="warlock", class_level=1, hit_die=8)
    ]
    character.level1_class_choices["warlock_invocation"] = "Lessons of the First Ones"
    feats = get_available_origin_feats(game_data)
    assert feats, "No origin feats available"
    character.level1_class_choices["warlock_lessons_feat"] = feats[0]["name"]
    return character


# ── FEAT: When ──────────────────────────────────────────────────────────────


@when(parsers.parse("the species origin feat {feat_name} is selected"))
def when_species_origin_feat_selected(
    character: Character, game_data: GameData, feat_name: str
):
    feat = game_data.find_feat(feat_name)
    assert feat, f"Unknown feat: {feat_name}"
    character.species_origin_feat = feat


# ── FEAT: Then ──────────────────────────────────────────────────────────────


@then(parsers.parse("the catalog contains {count:d} origin feats"))
def then_origin_feat_catalog_count(origin_feat_catalog: list[dict], count: int):
    assert len(origin_feat_catalog) == count


@then("the feat step requires a selection")
def then_feat_step_requires_selection(character: Character):
    assert _species_grants_origin_feat(character.species)


@then("the feat step does not require a selection")
def then_feat_step_no_selection(character: Character):
    assert not _species_grants_origin_feat(character.species)


@then(parsers.parse("the character species origin feat is {feat_name}"))
def then_species_origin_feat_is(character: Character, feat_name: str):
    assert character.species_origin_feat is not None, "No species origin feat set"
    assert character.species_origin_feat.get("name") == feat_name


@then("the character owns the warlock lessons feat")
def then_owned_feat_names_include_lessons(character: Character):
    lessons_name = character.level1_class_choices.get("warlock_lessons_feat", "")
    assert lessons_name, "No warlock lessons feat set"
    owned = get_owned_feat_names(character)
    assert lessons_name.casefold() in owned


@then(parsers.parse("{feat_name} appears in owned feat names"))
def then_feat_appears_in_owned(character: Character, feat_name: str):
    owned = get_owned_feat_names(character)
    assert feat_name.casefold() in owned


@then("the background feat has benefits with names and descriptions")
def then_background_feat_benefits_detail(character: Character):
    assert character.feat is not None
    for benefit in character.feat.get("benefits", []):
        assert benefit.get("name"), "Benefit missing name"
        assert benefit.get("description"), f"Benefit {benefit.get('name')} missing description"


@then("the species origin feat has benefits with names and descriptions")
def then_species_origin_feat_benefits_detail(character: Character):
    assert character.species_origin_feat is not None
    for benefit in character.species_origin_feat.get("benefits", []):
        assert benefit.get("name"), "Benefit missing name"
        assert benefit.get("description"), f"Benefit {benefit.get('name')} missing description"
