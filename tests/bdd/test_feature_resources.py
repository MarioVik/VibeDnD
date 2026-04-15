from __future__ import annotations

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from gui.data_loader import GameData
from models.character import Character
from models.class_level import ClassLevel
from models.feature_resource_utils import (
    class_feature_card_id,
    feat_card_id,
    get_active_feature_resources,
    get_feature_card_counter_text,
    get_feature_card_linked_resources,
    restore_feature_resources,
    scrub_feature_resource_state,
    species_trait_card_id,
    spend_feature_resource,
    subclass_feature_card_id,
)

scenarios("features/feature_resources.feature")


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


def _subclass_by_name(game_data: GameData, class_slug: str, subclass_name: str) -> dict:
    target = str(subclass_name or "").strip().casefold()
    for subclass in game_data.get_subclasses_for_class(class_slug):
        if str(subclass.get("name", "")).strip().casefold() == target:
            return subclass
    raise AssertionError(f"Unknown subclass {subclass_name} for {class_slug}")


def _build_character(game_data: GameData, class_slug: str, level: int) -> Character:
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
            class_level=class_level,
            hit_die=cls.get("hit_die", 8),
        )
        for class_level in range(1, level + 1)
    ]
    character.ability_scores.set_base("Charisma", 16)
    character.ability_scores.set_base("Wisdom", 16)
    character.ability_scores.set_base("Constitution", 14)
    return character


def _resource_by_label(character: Character, game_data: GameData, label: str) -> dict:
    for resource in get_active_feature_resources(character, game_data):
        if resource["resource_label"] == label:
            return resource
    raise AssertionError(f"Unknown feature resource: {label}")


@given(parsers.parse("a level {level:d} {class_slug} character"), target_fixture="character")
def levelled_character(game_data: GameData, level: int, class_slug: str) -> Character:
    return _build_character(game_data, class_slug, level)


@given(parsers.parse("the character is the species {species_name}"))
def character_species(character: Character, game_data: GameData, species_name: str):
    character.species = _species_by_name(game_data, species_name)


@given(parsers.parse("the character has the background feat {feat_name}"))
def character_background_feat(character: Character, game_data: GameData, feat_name: str):
    feat = game_data.find_feat(feat_name)
    assert feat is not None, feat_name
    character.background = {"name": "BDD Background", "feat": feat_name}
    character.feat = feat


@given(parsers.parse("the character has the subclass {subclass_name}"))
def character_subclass(character: Character, game_data: GameData, subclass_name: str):
    subclass = _subclass_by_name(game_data, character.character_class.get("slug", ""), subclass_name)
    for class_level in character.class_levels:
        if class_level.class_level >= 3:
            class_level.subclass_slug = subclass["slug"]
            break


@when(parsers.parse("the feature resource {label} is spent"))
def spend_feature(character: Character, game_data: GameData, label: str):
    resource = _resource_by_label(character, game_data, label)
    assert spend_feature_resource(character, game_data, resource["resource_id"], 1)


@when(parsers.parse("{amount:d} points of the feature resource {label} are spent"))
def spend_feature_points(character: Character, game_data: GameData, amount: int, label: str):
    resource = _resource_by_label(character, game_data, label)
    assert spend_feature_resource(character, game_data, resource["resource_id"], amount)


@when(parsers.parse("the character restores feature resources on a {rest_type} rest"))
def restore_feature_state(character: Character, game_data: GameData, rest_type: str):
    assert restore_feature_resources(character, game_data, rest_type)


@when(parsers.parse("the character changes species to {species_name}"))
def change_species(character: Character, game_data: GameData, species_name: str):
    character.species = _species_by_name(game_data, species_name)
    scrub_feature_resource_state(character, game_data)


@then(parsers.parse("the feature resource {label} shows {display_text}"))
def resource_display(character: Character, game_data: GameData, label: str, display_text: str):
    resource = _resource_by_label(character, game_data, label)
    assert resource["display_text"] == display_text


@then(parsers.parse("the class feature {feature_name} links {label} as {display_text}"))
def class_feature_link(character: Character, game_data: GameData, feature_name: str, label: str, display_text: str):
    class_slug = character.character_class.get("slug", "")
    matching_level = None
    for cl in character.class_levels:
        level_data = game_data.get_level_data(class_slug, cl.class_level) or {}
        names = {str(detail.get("name", "") or "") for detail in level_data.get("feature_details", []) or []}
        if feature_name in names:
            matching_level = cl.class_level
            break
    assert matching_level is not None, feature_name
    card_id = class_feature_card_id(class_slug, matching_level, feature_name)
    linked = get_feature_card_linked_resources(character, game_data, card_id)
    assert {"label": label, "display_text": display_text} in [
        {"label": entry["label"], "display_text": entry["display_text"]} for entry in linked
    ]


@then(parsers.parse("the species trait {trait_name} shows {display_text}"))
def species_trait_display(character: Character, game_data: GameData, trait_name: str, display_text: str):
    assert get_feature_card_counter_text(
        character,
        game_data,
        species_trait_card_id(character.species_name, trait_name),
    ) == display_text


@then(parsers.parse("the feat {feat_name} shows {display_text}"))
def feat_display(character: Character, game_data: GameData, feat_name: str, display_text: str):
    slot_key = "background" if character.feat and character.feat.get("name") == feat_name else "species_origin"
    assert get_feature_card_counter_text(
        character,
        game_data,
        feat_card_id(slot_key, feat_name),
    ) == display_text


@then(parsers.parse("the subclass feature {feature_name} links {label} as {display_text}"))
def subclass_feature_link(character: Character, game_data: GameData, feature_name: str, label: str, display_text: str):
    subclass_slug = character.current_subclass
    assert subclass_slug, "Character has no subclass"
    subclass = game_data.get_subclass(character.character_class.get("slug", ""), subclass_slug)
    assert subclass is not None
    feature_level = None
    for level_key, features in (subclass.get("features", {}) or {}).items():
        names = {str(feature.get("name", "") or "") for feature in features or []}
        if feature_name in names:
            feature_level = int(level_key)
            break
    assert feature_level is not None, feature_name
    card_id = subclass_feature_card_id(
        character.character_class.get("slug", ""),
        subclass_slug,
        feature_level,
        feature_name,
    )
    linked = get_feature_card_linked_resources(character, game_data, card_id)
    assert {"label": label, "display_text": display_text} in [
        {"label": entry["label"], "display_text": entry["display_text"]} for entry in linked
    ]


@then(parsers.parse("the species trait {trait_name} is no longer tracked"))
def species_trait_removed(character: Character, game_data: GameData, trait_name: str):
    assert get_feature_card_counter_text(
        character,
        game_data,
        species_trait_card_id("Orc", trait_name),
    ) == ""


@then("no feature resources are marked as spent")
def no_feature_resource_state(character: Character):
    assert getattr(character, "spent_feature_resources", {}) == {}
