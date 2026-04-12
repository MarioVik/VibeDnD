from __future__ import annotations

from pathlib import Path

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from gui.data_loader import GameData
from models.character import Character
from models.class_level import ClassLevel
from models.language_utils import RARE_LANGUAGES, STANDARD_LANGUAGES, compute_language_sources
from models.level1_class_rules import (
    get_level1_creation_choice_lines,
    get_level1_feature_choice_annotations,
    get_available_fighting_styles,
    get_available_origin_feats,
    get_effective_armor_proficiencies,
    get_effective_cantrips_known,
    get_effective_prepared_spells,
    get_effective_weapon_proficiencies,
    get_level1_feature_catalog,
    get_tome_cantrip_options,
    get_tome_ritual_options,
    get_unmet_level1_class_requirements,
    get_warlock_invocation_binding_options,
    get_weapon_mastery_count,
    get_weapon_mastery_options,
    scrub_level1_class_choices,
)
from models.spell_grant_utils import (
    apply_default_spell_grant_abilities,
    character_has_spell_step_content,
    format_spellbook_entry_label,
    get_active_free_cast_resources,
    get_active_spell_grant_sources,
    get_free_spell_summary_entries,
    get_spendable_free_cast_resources,
    get_selectable_class_cantrip_options,
    get_selectable_class_spell_options,
    get_spell_grant_choice_value,
    get_spell_grant_requirements,
    get_spellbook_entries,
    restore_free_casts,
    scrub_spell_grant_choices,
    spend_free_cast,
    set_spell_grant_choice_value,
)
from models.standard_actions import build_standard_actions

scenarios("features/level1_feature_catalog.feature")
scenarios("features/level1_class_completion.feature")
scenarios("features/level1_class_integrations.feature")
scenarios("features/level1_spell_grants.feature")

REPO_ROOT = Path(__file__).resolve().parents[2]
DOC_PATH = REPO_ROOT / "docs" / "testing" / "level1-class-creation.md"

VALID_CATEGORIES = {
    "document-only",
    "auto grant",
    "existing-step choice",
    "new class-feature choice",
}
VALID_WIZARD_SURFACES = {
    "none",
    "skills",
    "class_features",
    "spells",
    "languages",
    "equipment",
}


@pytest.fixture(scope="session")
def game_data() -> GameData:
    return GameData()


def _class_by_slug(game_data: GameData, class_slug: str) -> dict:
    for cls in game_data.classes:
        if cls.get("slug") == class_slug:
            return cls
    raise AssertionError(f"Unknown class slug: {class_slug}")


def _species_by_name(game_data: GameData, species_name: str) -> dict:
    species = game_data.species_by_name.get(species_name)
    if not species:
        raise AssertionError(f"Unknown species: {species_name}")
    return species


def _set_species(
    character: Character,
    game_data: GameData,
    species_name: str,
    *,
    sub_choice: str = "",
):
    character.species = _species_by_name(game_data, species_name)
    character.species_sub_choice = sub_choice or None


def _set_species_origin_feat(character: Character, game_data: GameData, feat_name: str):
    feat = game_data.find_feat(feat_name)
    if not feat:
        raise AssertionError(f"Unknown feat: {feat_name}")
    character.species_origin_feat = feat


def _set_background_feat(character: Character, feat_name: str):
    character.background = {"name": "BDD Background", "feat": feat_name}


def _source_by_label(character: Character, game_data: GameData, label: str) -> dict:
    for source in get_active_spell_grant_sources(character, game_data):
        if source["source_label"] == label:
            return source
    raise AssertionError(f"Unknown active spell grant source: {label}")


def _active_free_cast_resource_by_label(character: Character, game_data: GameData, label: str) -> dict:
    for resource in get_active_free_cast_resources(character, game_data):
        if resource["label"] == label:
            return resource
    raise AssertionError(f"Unknown active free-cast resource: {label}")


def _spendable_free_cast_resource_by_label(character: Character, game_data: GameData, label: str) -> dict:
    for resource in get_spendable_free_cast_resources(character, game_data):
        if resource["label"] == label:
            return resource
    raise AssertionError(f"Unknown spendable free-cast resource: {label}")


def _refresh_spell_grants(character: Character, game_data: GameData):
    scrub_level1_class_choices(character, game_data)
    apply_default_spell_grant_abilities(character, game_data)
    scrub_spell_grant_choices(character, game_data)


def _choose_default_spell_grant_choices(character: Character, game_data: GameData):
    _refresh_spell_grants(character, game_data)
    class_ability = str((character.character_class or {}).get("spellcasting_ability", "") or "").strip()

    for source in get_active_spell_grant_sources(character, game_data):
        source_id = source["source_id"]

        if source["source_list_options"] and not str(
            get_spell_grant_choice_value(character, source_id, "source_list", "") or ""
        ).strip():
            set_spell_grant_choice_value(
                character,
                source_id,
                "source_list",
                source["source_list_options"][0],
            )
            _refresh_spell_grants(character, game_data)
            source = _source_by_label(character, game_data, source["source_label"])

        if source.get("ability_choice_required") and not str(
            get_spell_grant_choice_value(character, source_id, "ability", "") or ""
        ).strip():
            ability = class_ability or source["ability_options"][0]
            set_spell_grant_choice_value(character, source_id, "ability", ability)

        if source["cantrip_choice_count"]:
            set_spell_grant_choice_value(
                character,
                source_id,
                "cantrips",
                list(source["cantrip_options"][: source["cantrip_choice_count"]]),
            )

        if source["spell_choice_count"]:
            set_spell_grant_choice_value(
                character,
                source_id,
                "spells",
                list(source["spell_options"][: source["spell_choice_count"]]),
            )

    _refresh_spell_grants(character, game_data)


def _table_rows(path: Path, heading: str) -> list[dict[str, str]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    capture = False
    headers: list[str] | None = None
    rows: list[dict[str, str]] = []

    for line in lines:
        if line.strip() == heading:
            capture = True
            continue
        if capture and line.startswith("## "):
            break
        if not capture or not line.startswith("|"):
            continue

        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if headers is None:
            headers = cells
            continue
        if all(not cell.replace("-", "").replace(":", "").strip() for cell in cells):
            continue
        rows.append(dict(zip(headers, cells, strict=False)))

    return rows


def _feature_matrix_rows() -> list[dict[str, str]]:
    return _table_rows(DOC_PATH, "## Feature Matrix")


def _build_level1_character(game_data: GameData, class_slug: str) -> Character:
    cls = _class_by_slug(game_data, class_slug)
    character = Character(
        name=f"BDD {cls['name']}",
        character_class=cls,
        equipment_choice_class="",
        equipment_choice_background="A",
    )
    character.class_levels = [
        ClassLevel(
            class_slug=class_slug,
            class_level=1,
            hit_die=cls.get("hit_die", 8),
        )
    ]
    character.ability_scores.set_base("Wisdom", 16)
    character.ability_scores.set_base("Intelligence", 10)
    return character


def _choose_class_skills(character: Character):
    skill_choices = (character.character_class or {}).get("skill_choices", {})
    options = [str(option).strip() for option in skill_choices.get("options", [])]
    count = int(skill_choices.get("count", 0) or 0)
    character.selected_skills = options[:count]


def _choose_languages(character: Character):
    sources = compute_language_sources(character)
    available = list(STANDARD_LANGUAGES)
    if sources.get("can_choose_rare"):
        available.extend(RARE_LANGUAGES)
    character.chosen_languages = [
        language
        for language in available
        if language not in set(sources.get("auto", []))
    ][: int(sources.get("free_count", 0) or 0)]


def _first_equipment_option(character: Character) -> str:
    for option in (character.character_class or {}).get("starting_equipment", []):
        letter = str(option.get("option", "")).strip()
        if letter:
            return letter
    return ""


def _select_spell_choices(
    character: Character,
    game_data: GameData,
    *,
    preferred_cantrips: list[str] | None = None,
    preferred_spells: list[str] | None = None,
):
    class_name = (character.character_class or {}).get("name", "")
    preferred_cantrips = preferred_cantrips or []
    preferred_spells = preferred_spells or []

    cantrip_target = get_effective_cantrips_known(character)
    cantrip_options = get_selectable_class_cantrip_options(character, game_data)
    selected_cantrips: list[str] = []
    for spell_name in preferred_cantrips + cantrip_options:
        if spell_name in cantrip_options and spell_name not in selected_cantrips:
            selected_cantrips.append(spell_name)
        if len(selected_cantrips) >= cantrip_target:
            break
    character.selected_cantrips = selected_cantrips

    spell_target = get_effective_prepared_spells(character)
    spell_options = get_selectable_class_spell_options(character, game_data, level=1)
    selected_spells: list[str] = []
    for spell_name in preferred_spells + spell_options:
        if spell_name in spell_options and spell_name not in selected_spells:
            selected_spells.append(spell_name)
        if len(selected_spells) >= spell_target:
            break
    character.selected_spells = selected_spells


def _select_default_level1_choices(
    character: Character,
    game_data: GameData,
    *,
    warlock_invocation: str | None = None,
):
    slug = (character.character_class or {}).get("slug", "")
    choices = character.level1_class_choices

    if slug == "cleric":
        choices["divine_order"] = "Protector"
    elif slug == "druid":
        choices["primal_order"] = "Warden"
    elif slug == "fighter":
        styles = get_available_fighting_styles(game_data)
        assert styles, "Expected fighting styles in feat data"
        choices["fighting_style"] = styles[0]["name"]

    mastery_count = get_weapon_mastery_count(character)
    if mastery_count:
        options = get_weapon_mastery_options(character, game_data)
        choices["weapon_mastery"] = options[:mastery_count]

    if slug == "warlock":
        invocation = warlock_invocation or "Armor of Shadows"
        choices["warlock_invocation"] = invocation


def _finalize_warlock_nested_choices(character: Character, game_data: GameData):
    invocation = str(character.level1_class_choices.get("warlock_invocation", "")).strip()
    if invocation in {"Agonizing Blast", "Eldritch Spear", "Repelling Blast"}:
        bindings = get_warlock_invocation_binding_options(character, game_data)
        assert bindings, f"Expected cantrip binding options for {invocation}"
        character.level1_class_choices["warlock_invocation_cantrip"] = bindings[0]
    elif invocation == "Pact of the Tome":
        character.level1_class_choices["warlock_tome_cantrips"] = get_tome_cantrip_options(
            game_data
        )[:3]
        character.level1_class_choices["warlock_tome_rituals"] = get_tome_ritual_options(
            game_data
        )[:2]
    elif invocation == "Lessons of the First Ones":
        feats = get_available_origin_feats(game_data)
        assert feats, "Expected origin feats for Lessons of the First Ones"
        character.level1_class_choices["warlock_lessons_feat"] = feats[0]["name"]


def _complete_level1_character(
    game_data: GameData,
    class_slug: str,
    *,
    warlock_invocation: str | None = None,
) -> Character:
    character = _build_level1_character(game_data, class_slug)

    _select_default_level1_choices(
        character,
        game_data,
        warlock_invocation=warlock_invocation,
    )
    scrub_level1_class_choices(character, game_data)
    apply_default_spell_grant_abilities(character, game_data)

    _choose_class_skills(character)
    if class_slug == "rogue":
        character.class_levels[0].new_expertise = character.selected_skills[:2]

    preferred_cantrips: list[str] = []
    if warlock_invocation in {"Agonizing Blast", "Eldritch Spear", "Repelling Blast"}:
        preferred_cantrips = ["Eldritch Blast"]

    _select_spell_choices(
        character,
        game_data,
        preferred_cantrips=preferred_cantrips,
    )
    _finalize_warlock_nested_choices(character, game_data)
    _choose_default_spell_grant_choices(character, game_data)
    _select_spell_choices(
        character,
        game_data,
        preferred_cantrips=preferred_cantrips,
    )
    _choose_languages(character)
    character.equipment_choice_class = _first_equipment_option(character)
    scrub_level1_class_choices(character, game_data)
    _refresh_spell_grants(character, game_data)

    blockers = get_unmet_level1_class_requirements(character, game_data)
    assert blockers == [], f"Expected complete character for {class_slug}, got {blockers}"
    return character


def _remove_requirement(character: Character, requirement_id: str):
    if requirement_id == "class-cantrips":
        character.selected_cantrips = character.selected_cantrips[:-1]
        return
    if requirement_id == "class-spells":
        character.selected_spells = character.selected_spells[:-1]
        return
    if requirement_id == "class-skills":
        character.selected_skills = character.selected_skills[:-1]
        return
    if requirement_id == "class-languages":
        character.chosen_languages = character.chosen_languages[:-1]
        return
    if requirement_id == "class-equipment":
        character.equipment_choice_class = ""
        return
    if requirement_id == "divine-order":
        character.level1_class_choices.pop("divine_order", None)
        return
    if requirement_id == "primal-order":
        character.level1_class_choices.pop("primal_order", None)
        return
    if requirement_id == "fighting-style":
        character.level1_class_choices.pop("fighting_style", None)
        return
    if requirement_id == "weapon-mastery":
        current = list(character.level1_class_choices.get("weapon_mastery", []))
        character.level1_class_choices["weapon_mastery"] = current[:-1]
        return
    if requirement_id == "rogue-expertise":
        character.class_levels[0].new_expertise = character.class_levels[0].new_expertise[:-1]
        return
    if requirement_id == "warlock-invocation":
        for key in (
            "warlock_invocation",
            "warlock_invocation_cantrip",
            "warlock_tome_cantrips",
            "warlock_tome_rituals",
            "warlock_lessons_feat",
        ):
            character.level1_class_choices.pop(key, None)
        return
    if requirement_id == "warlock-invocation-cantrip":
        character.level1_class_choices.pop("warlock_invocation_cantrip", None)
        return
    if requirement_id == "warlock-tome-cantrips":
        current = list(character.level1_class_choices.get("warlock_tome_cantrips", []))
        character.level1_class_choices["warlock_tome_cantrips"] = current[:-1]
        return
    if requirement_id == "warlock-tome-rituals":
        current = list(character.level1_class_choices.get("warlock_tome_rituals", []))
        character.level1_class_choices["warlock_tome_rituals"] = current[:-1]
        return
    if requirement_id == "warlock-lessons-feat":
        character.level1_class_choices.pop("warlock_lessons_feat", None)
        return
    raise AssertionError(f"Unsupported requirement removal: {requirement_id}")


def _blocker_ids(character: Character, game_data: GameData) -> set[str]:
    blockers = get_unmet_level1_class_requirements(character, game_data)
    return {blocker["id"] for blocker in blockers}


@given("the level 1 class feature catalog", target_fixture="catalog")
def given_catalog(game_data: GameData) -> list[dict]:
    return get_level1_feature_catalog(game_data)


@given(parsers.parse("a level 1 {class_slug} character"), target_fixture="character")
def given_level1_character(game_data: GameData, class_slug: str) -> Character:
    return _build_level1_character(game_data, class_slug)


@given(
    parsers.parse("a fully completed level 1 {class_slug} character"),
    target_fixture="character",
)
def given_completed_character(game_data: GameData, class_slug: str) -> Character:
    return _complete_level1_character(game_data, class_slug)


@given(
    parsers.parse(
        "a fully completed level 1 warlock character with the {invocation} invocation"
    ),
    target_fixture="character",
)
def given_completed_warlock(game_data: GameData, invocation: str) -> Character:
    return _complete_level1_character(
        game_data,
        "warlock",
        warlock_invocation=invocation,
    )


@given(parsers.parse("the character is the species {species_name}"))
def given_character_species(character: Character, game_data: GameData, species_name: str):
    _set_species(character, game_data, species_name)
    _refresh_spell_grants(character, game_data)


@given(parsers.parse("the character is the species {species_name} with the {sub_choice} lineage"))
def given_character_species_subchoice(
    character: Character,
    game_data: GameData,
    species_name: str,
    sub_choice: str,
):
    _set_species(character, game_data, species_name, sub_choice=sub_choice)
    _refresh_spell_grants(character, game_data)


@given(parsers.parse("the character has the species origin feat {feat_name}"))
def given_species_origin_feat(character: Character, game_data: GameData, feat_name: str):
    _set_species_origin_feat(character, game_data, feat_name)
    _refresh_spell_grants(character, game_data)


@given(parsers.parse("the character has the background feat {feat_name}"))
def given_background_feat(character: Character, game_data: GameData, feat_name: str):
    _set_background_feat(character, feat_name)
    _refresh_spell_grants(character, game_data)


@given(parsers.parse("the {source_label} source uses {ability} as its spellcasting ability"))
def given_source_ability_choice(
    character: Character,
    game_data: GameData,
    source_label: str,
    ability: str,
):
    source = _source_by_label(character, game_data, source_label)
    set_spell_grant_choice_value(character, source["source_id"], "ability", ability)
    _refresh_spell_grants(character, game_data)


@when(parsers.parse("the {requirement_id} requirement is removed from that character"))
def when_requirement_removed(character: Character, requirement_id: str, game_data: GameData):
    _remove_requirement(character, requirement_id)
    scrub_level1_class_choices(character, game_data)


@when("the cleric chooses the Thaumaturge order")
def when_cleric_chooses_thaumaturge(character: Character, game_data: GameData):
    character.level1_class_choices["divine_order"] = "Thaumaturge"
    scrub_level1_class_choices(character, game_data)


@when("the cleric chooses the Protector order")
def when_cleric_chooses_protector(character: Character, game_data: GameData):
    character.level1_class_choices["divine_order"] = "Protector"
    scrub_level1_class_choices(character, game_data)


@when("the druid chooses the Magician order")
def when_druid_chooses_magician(character: Character, game_data: GameData):
    character.level1_class_choices["primal_order"] = "Magician"
    scrub_level1_class_choices(character, game_data)


@when("the druid chooses the Warden order")
def when_druid_chooses_warden(character: Character, game_data: GameData):
    character.level1_class_choices["primal_order"] = "Warden"
    scrub_level1_class_choices(character, game_data)


@when("the rogue selects a non-proficient expertise skill")
def when_rogue_selects_invalid_expertise(character: Character):
    character.class_levels[0].new_expertise = ["Arcana", character.selected_skills[0]]


@when("the invocation cantrip binding is removed from that character")
def when_invocation_binding_removed(character: Character, game_data: GameData):
    _remove_requirement(character, "warlock-invocation-cantrip")
    scrub_level1_class_choices(character, game_data)


@when("one Pact of the Tome cantrip is removed from that character")
def when_tome_cantrip_removed(character: Character, game_data: GameData):
    _remove_requirement(character, "warlock-tome-cantrips")
    scrub_level1_class_choices(character, game_data)


@when("one Pact of the Tome ritual is removed from that character")
def when_tome_ritual_removed(character: Character, game_data: GameData):
    _remove_requirement(character, "warlock-tome-rituals")
    scrub_level1_class_choices(character, game_data)


@when("the granted origin feat choice is removed from that character")
def when_lessons_feat_removed(character: Character, game_data: GameData):
    _remove_requirement(character, "warlock-lessons-feat")
    scrub_level1_class_choices(character, game_data)


@when("spell grant defaults are applied")
def when_spell_grant_defaults_applied(character: Character, game_data: GameData):
    _refresh_spell_grants(character, game_data)


@when(parsers.parse("the {source_label} source spell list is set to {list_name}"))
def when_spell_grant_source_list_selected(
    character: Character,
    game_data: GameData,
    source_label: str,
    list_name: str,
):
    source = _source_by_label(character, game_data, source_label)
    set_spell_grant_choice_value(character, source["source_id"], "source_list", list_name)
    _refresh_spell_grants(character, game_data)


@when(parsers.parse("the free cast {label} is spent"))
def when_free_cast_spent(character: Character, game_data: GameData, label: str):
    resource = _spendable_free_cast_resource_by_label(character, game_data, label)
    assert spend_free_cast(character, game_data, resource["resource_id"])


@when(parsers.parse("the character restores free casts on a {rest_type} rest"))
def when_free_casts_restored(character: Character, game_data: GameData, rest_type: str):
    assert rest_type in {"short", "long"}
    restore_free_casts(character, game_data, rest_type)


@when(parsers.parse("the character changes species to {species_name}"))
def when_character_changes_species(character: Character, game_data: GameData, species_name: str):
    _set_species(character, game_data, species_name)
    _refresh_spell_grants(character, game_data)


@then("the markdown specification documents every level 1 class feature")
def then_markdown_documents_every_feature(catalog: list[dict]):
    doc_rows = _feature_matrix_rows()
    doc_index = {(row["Class"], row["Feature"]): row for row in doc_rows}
    catalog_index = {
        (entry["class_name"], entry["feature_name"]): entry for entry in catalog
    }

    assert set(doc_index) == set(catalog_index)
    for key, entry in catalog_index.items():
        row = doc_index[key]
        assert row["Category"] == entry["category"]
        assert row["Wizard Surface"] == entry["wizard_surface"]


@then("every catalog entry has a valid category and wizard surface")
def then_catalog_entries_are_classified(catalog: list[dict]):
    assert catalog
    for entry in catalog:
        assert entry["category"] in VALID_CATEGORIES
        assert entry["wizard_surface"] in VALID_WIZARD_SURFACES


@then(parsers.parse("the {requirement_id} blocker is reported for that character"))
def then_blocker_is_reported(
    character: Character,
    game_data: GameData,
    requirement_id: str,
):
    assert requirement_id in _blocker_ids(character, game_data)


@then("the character has no unmet level 1 requirements")
def then_character_has_no_level1_blockers(character: Character, game_data: GameData):
    assert get_unmet_level1_class_requirements(character, game_data) == []


@then("the cleric gains 1 extra cantrip choice")
def then_cleric_gains_extra_cantrip(character: Character):
    base_count = int((character.character_class or {}).get("cantrips_known") or 0)
    assert get_effective_cantrips_known(character) == base_count + 1


@then("the cleric gains a Wisdom bonus to Arcana and Religion")
def then_cleric_gains_skill_bonus(character: Character):
    assert character.skill_modifier("Arcana") == 3
    assert character.skill_modifier("Religion") == 3


@then("the cleric gains heavy armor and martial weapon proficiency")
def then_cleric_gains_proficiencies(character: Character):
    armor = get_effective_armor_proficiencies(character)
    weapons = get_effective_weapon_proficiencies(character)
    assert "Heavy armor" in armor
    assert "Martial weapons" in weapons


@then("the druid gains 1 extra cantrip choice")
def then_druid_gains_extra_cantrip(character: Character):
    base_count = int((character.character_class or {}).get("cantrips_known") or 0)
    assert get_effective_cantrips_known(character) == base_count + 1


@then("the druid gains a Wisdom bonus to Arcana and Nature")
def then_druid_gains_skill_bonus(character: Character):
    assert character.skill_modifier("Arcana") == 3
    assert character.skill_modifier("Nature") == 3


@then("the druid gains medium armor and martial weapon proficiency")
def then_druid_gains_proficiencies(character: Character):
    armor = get_effective_armor_proficiencies(character)
    weapons = get_effective_weapon_proficiencies(character)
    assert "Medium armor" in armor
    assert "Martial weapons" in weapons


@then(parsers.parse("the {class_slug} requires {count:d} weapon mastery choices"))
def then_weapon_mastery_count(character: Character, class_slug: str, count: int):
    assert (character.character_class or {}).get("slug") == class_slug
    assert get_weapon_mastery_count(character) == count


@then("the rogue receives 3 total level 1 language choices")
def then_rogue_has_extra_language(character: Character):
    sources = compute_language_sources(character)
    assert sources["free_count"] == 3


@then("the rogue weapon mastery pool includes Dagger")
def then_rogue_pool_includes_dagger(character: Character, game_data: GameData):
    assert "Dagger" in get_weapon_mastery_options(character, game_data)


@then("the rogue weapon mastery pool includes Shortsword")
def then_rogue_pool_includes_shortsword(character: Character, game_data: GameData):
    assert "Shortsword" in get_weapon_mastery_options(character, game_data)


@then("the rogue weapon mastery pool excludes Greatsword")
def then_rogue_pool_excludes_greatsword(character: Character, game_data: GameData):
    assert "Greatsword" not in get_weapon_mastery_options(character, game_data)


@then("the Primal Order feature annotation shows Warden")
def then_druid_feature_annotation(character: Character):
    annotations = get_level1_feature_choice_annotations(character)
    assert annotations["Primal Order"] == ["Selected Order: Warden"]


@then("the Weapon Mastery feature annotation shows the selected weapons")
def then_weapon_mastery_annotation(character: Character):
    annotations = get_level1_feature_choice_annotations(character)
    selected = character.level1_class_choices.get("weapon_mastery", [])
    assert annotations["Weapon Mastery"] == [
        f"Selected Weapons: {', '.join(selected)}"
    ]


@then("the level 1 creation choice summary lists skills, expertise, languages, and equipment")
def then_creation_choice_summary_lists_core_choices(character: Character):
    lines = get_level1_creation_choice_lines(character)
    assert any(line.startswith("Class Skills: ") for line in lines)
    assert any(line.startswith("Expertise: ") for line in lines)
    assert any(line.startswith("Chosen Languages: ") for line in lines)
    assert any(line.startswith("Starting Equipment: ") for line in lines)


@then("the Eldritch Invocations feature annotation shows Pact of the Tome details")
def then_warlock_invocation_annotation(character: Character):
    annotations = get_level1_feature_choice_annotations(character)
    lines = annotations["Eldritch Invocations"]
    assert "Selected Invocation: Pact of the Tome" in lines
    assert any(line.startswith("Tome Cantrips: ") for line in lines)
    assert any(line.startswith("Tome Rituals: ") for line in lines)


@then("the character has spell step content")
def then_character_has_spell_step(character: Character, game_data: GameData):
    assert character_has_spell_step_content(character, game_data)


@then(parsers.parse("the spellbook includes {spell_name} granted by {source_label}"))
def then_spellbook_includes_granted_spell(
    character: Character,
    game_data: GameData,
    spell_name: str,
    source_label: str,
):
    entries = {
        entry["spell_name"]: entry
        for entry in get_spellbook_entries(character, game_data)
    }
    assert spell_name in entries
    assert source_label in entries[spell_name]["source_labels"]


@then(parsers.parse("the spellbook does not include {spell_name}"))
def then_spellbook_excludes_spell(character: Character, game_data: GameData, spell_name: str):
    assert spell_name not in {
        entry["spell_name"] for entry in get_spellbook_entries(character, game_data)
    }


@then(parsers.parse("the spellbook includes {count:d} cantrips total"))
def then_spellbook_cantrip_count(character: Character, game_data: GameData, count: int):
    assert sum(
        1 for entry in get_spellbook_entries(character, game_data) if int(entry.get("level", 0) or 0) == 0
    ) == count


@then(parsers.parse("{spell_name} is not a selectable base cantrip for that character"))
def then_spell_not_selectable_cantrip(character: Character, game_data: GameData, spell_name: str):
    assert spell_name not in get_selectable_class_cantrip_options(character, game_data)


@then(parsers.parse("{spell_name} is not a selectable base level 1 spell for that character"))
def then_spell_not_selectable_level1(character: Character, game_data: GameData, spell_name: str):
    assert spell_name not in get_selectable_class_spell_options(character, game_data, level=1)


@then(parsers.parse("{spell_name} is a selectable base level 1 spell for that character"))
def then_spell_is_selectable_level1(character: Character, game_data: GameData, spell_name: str):
    assert spell_name in get_selectable_class_spell_options(character, game_data, level=1)


@then(parsers.parse("the {source_label} source requires a spell list choice"))
def then_source_requires_spell_list(character: Character, game_data: GameData, source_label: str):
    source = _source_by_label(character, game_data, source_label)
    requirements = get_spell_grant_requirements(character, game_data)
    requirement_ids = {item["id"] for item in requirements}
    assert f"{source['source_id']}:source_list" in requirement_ids


@then(
    parsers.parse(
        "the {source_label} source requires {cantrip_count:d} cantrip choices and {spell_count:d} spell choices"
    )
)
def then_source_requires_spell_choices(
    character: Character,
    game_data: GameData,
    source_label: str,
    cantrip_count: int,
    spell_count: int,
):
    source = _source_by_label(character, game_data, source_label)
    requirements = get_spell_grant_requirements(character, game_data)
    requirement_ids = {item["id"] for item in requirements}
    if cantrip_count:
        assert source["cantrip_choice_count"] == cantrip_count
        assert f"{source['source_id']}:cantrips" in requirement_ids
    if spell_count:
        assert source["spell_choice_count"] == spell_count
        assert f"{source['source_id']}:spells" in requirement_ids


@then(parsers.parse("the {source_label} source uses {ability} as its spellcasting ability"))
def then_source_uses_ability(
    character: Character,
    game_data: GameData,
    source_label: str,
    ability: str,
):
    source = _source_by_label(character, game_data, source_label)
    assert get_spell_grant_choice_value(character, source["source_id"], "ability", "") == ability


@then(parsers.parse("the {source_label} source offers {count:d} cantrip choice instead of a fixed cantrip"))
def then_source_offers_cantrip_choice(
    character: Character,
    game_data: GameData,
    source_label: str,
    count: int,
):
    source = _source_by_label(character, game_data, source_label)
    assert source["cantrip_choice_count"] == count
    assert source["granted_entries"] == []


@then(parsers.parse("the free spell summary includes {label} - {cadence}"))
def then_free_spell_summary_includes(
    character: Character,
    game_data: GameData,
    label: str,
    cadence: str,
):
    assert any(
        entry["label"] == label and entry["cadence"] == cadence
        for entry in get_free_spell_summary_entries(character, game_data)
    )


@then(parsers.parse("the free spell summary does not include {label}"))
def then_free_spell_summary_excludes(character: Character, game_data: GameData, label: str):
    assert label not in {
        entry["label"] for entry in get_free_spell_summary_entries(character, game_data)
    }


@then(parsers.parse("the shared free cast {label} applies to {spell_name}"))
def then_shared_free_cast_applies_to_spell(
    character: Character,
    game_data: GameData,
    label: str,
    spell_name: str,
):
    resource = _active_free_cast_resource_by_label(character, game_data, label)
    assert resource["kind"] == "shared_pool"
    assert spell_name in resource["eligible_spell_names"]


@then(parsers.parse("the spellbook entry for {spell_name} lists free casting {detail}"))
def then_spellbook_entry_lists_free_cast_detail(
    character: Character,
    game_data: GameData,
    spell_name: str,
    detail: str,
):
    entry = next(
        item for item in get_spellbook_entries(character, game_data) if item["spell_name"] == spell_name
    )
    assert detail in (entry.get("free_casts", []) or [])


@then(parsers.parse("{label} is not a spendable free cast"))
def then_free_cast_not_spendable(character: Character, game_data: GameData, label: str):
    assert label not in {
        resource["label"] for resource in get_spendable_free_cast_resources(character, game_data)
    }


@then("no free casts are marked as spent")
def then_no_free_casts_marked_as_spent(character: Character):
    assert getattr(character, "used_free_casts", {}) == {}


@then(parsers.parse("{spell_name} is tagged as a Dragonmark spell"))
def then_spell_is_dragonmark(character: Character, game_data: GameData, spell_name: str):
    entries = {
        entry["spell_name"]: entry
        for entry in get_spellbook_entries(character, game_data)
    }
    assert entries[spell_name]["dragonmark_eligible"] is True


@then(parsers.parse("the formatted spellbook label for {spell_name} includes {suffix}"))
def then_formatted_spellbook_label_includes(
    character: Character,
    game_data: GameData,
    spell_name: str,
    suffix: str,
):
    entry = next(
        entry for entry in get_spellbook_entries(character, game_data) if entry["spell_name"] == spell_name
    )
    assert suffix in format_spellbook_entry_label(entry)


@then(parsers.parse("the standard actions include the cantrip attack {spell_name}"))
def then_standard_actions_include_cantrip_attack(
    character: Character,
    game_data: GameData,
    spell_name: str,
):
    spells_by_name = {spell.get("name", ""): spell for spell in game_data.spells}
    actions = build_standard_actions(
        character,
        spells_by_name=spells_by_name,
        game_data=game_data,
    )
    assert any(
        action.get("kind") == "cantrip" and action.get("name") == spell_name
        for action in actions
    )
