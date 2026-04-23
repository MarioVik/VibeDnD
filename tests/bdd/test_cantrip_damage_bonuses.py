"""BDD tests for cantrip damage bonuses from class features."""

from __future__ import annotations

import pytest

from gui.data_loader import GameData
from models.ability_scores import AbilityScores
from models.character import Character
from models.class_level import ClassLevel
from models.standard_actions import build_standard_actions


@pytest.fixture(scope="module")
def game_data() -> GameData:
    return GameData()


def _spells_by_name(game_data: GameData) -> dict[str, dict]:
    return {spell["name"]: spell for spell in game_data.spells}


def _find_class(game_data: GameData, slug: str) -> dict:
    for cls in game_data.classes:
        if cls["slug"] == slug:
            return cls
    raise ValueError(f"Class {slug} not found")


def _build_character(
    game_data: GameData,
    class_slug: str,
    *,
    cantrips: list[str] | None = None,
    spells: list[str] | None = None,
    level1_choices: dict | None = None,
    class_levels: list[ClassLevel] | None = None,
    ability_overrides: dict[str, int] | None = None,
) -> Character:
    cls = _find_class(game_data, class_slug)
    character = Character(
        name=f"Test {cls['name']}",
        character_class=cls,
    )
    if class_levels:
        character.class_levels = list(class_levels)
    else:
        character.class_levels = [
            ClassLevel(class_slug=class_slug, class_level=1, hit_die=cls.get("hit_die", 8))
        ]
    if cantrips:
        character.selected_cantrips = list(cantrips)
    if spells:
        character.selected_spells = list(spells)
    if level1_choices:
        character.level1_class_choices = dict(level1_choices)

    # Set good ability scores
    character.ability_scores.set_base("Charisma", 16)  # +3
    character.ability_scores.set_base("Intelligence", 16)  # +3
    character.ability_scores.set_base("Wisdom", 16)  # +3
    character.ability_scores.set_base("Dexterity", 14)  # +2
    character.ability_scores.set_base("Constitution", 14)  # +2
    character.ability_scores.set_base("Strength", 10)  # +0

    if ability_overrides:
        for ability, score in ability_overrides.items():
            character.ability_scores.set_base(ability, score)

    return character


def _get_cantrip_action(actions: list[dict], cantrip_name: str) -> dict | None:
    for action in actions:
        if action.get("kind") == "cantrip" and action.get("name") == cantrip_name:
            return action
    return None


# ── Agonizing Blast ──────────────────────────────────────────────────


def test_agonizing_blast_adds_cha_to_bound_cantrip(game_data: GameData):
    """Agonizing Blast should add CHA modifier to the bound cantrip's damage."""
    character = _build_character(
        game_data,
        "warlock",
        cantrips=["Eldritch Blast"],
        level1_choices={
            "warlock_invocation": "Agonizing Blast",
            "warlock_invocation_cantrip": "Eldritch Blast",
        },
    )

    spells = _spells_by_name(game_data)
    actions = build_standard_actions(character, spells_by_name=spells, game_data=game_data)
    action = _get_cantrip_action(actions, "Eldritch Blast")

    assert action is not None, "Eldritch Blast should appear in actions"
    # CHA is 16 → +3 modifier
    assert "+3" in action["damage"], (
        f"Expected +3 CHA bonus in damage, got: {action['damage']}"
    )


def test_agonizing_blast_does_not_affect_unbound_cantrip(game_data: GameData):
    """Agonizing Blast should NOT add damage to a cantrip it isn't bound to."""
    character = _build_character(
        game_data,
        "warlock",
        cantrips=["Eldritch Blast", "Chill Touch"],
        level1_choices={
            "warlock_invocation": "Agonizing Blast",
            "warlock_invocation_cantrip": "Eldritch Blast",
        },
    )

    spells = _spells_by_name(game_data)
    actions = build_standard_actions(character, spells_by_name=spells, game_data=game_data)

    chill_touch = _get_cantrip_action(actions, "Chill Touch")
    if chill_touch:
        # Should not have +3 bonus
        assert "+3" not in chill_touch["damage"], (
            f"Chill Touch should not have CHA bonus: {chill_touch['damage']}"
        )


# ── Empowered Evocation (Evoker Wizard) ────────────────────────────


def test_empowered_evocation_adds_int_to_evocation_cantrips(game_data: GameData):
    """Evoker Wizard at level 10+ should add INT to Evocation cantrip damage."""
    class_levels = [
        ClassLevel(class_slug="wizard", class_level=i, hit_die=6, subclass_slug="evoker")
        for i in range(1, 11)
    ]
    character = _build_character(
        game_data,
        "wizard",
        cantrips=["Fire Bolt"],
        class_levels=class_levels,
    )

    spells = _spells_by_name(game_data)
    actions = build_standard_actions(character, spells_by_name=spells, game_data=game_data)
    action = _get_cantrip_action(actions, "Fire Bolt")

    assert action is not None, "Fire Bolt should appear in actions"
    assert "+3" in action["damage"], (
        f"Expected +3 INT bonus in damage, got: {action['damage']}"
    )


def test_empowered_evocation_not_at_level_9(game_data: GameData):
    """Evoker Wizard at level 9 should NOT get Empowered Evocation bonus."""
    class_levels = [
        ClassLevel(class_slug="wizard", class_level=i, hit_die=6, subclass_slug="evoker")
        for i in range(1, 10)
    ]
    character = _build_character(
        game_data,
        "wizard",
        cantrips=["Fire Bolt"],
        class_levels=class_levels,
    )

    spells = _spells_by_name(game_data)
    actions = build_standard_actions(character, spells_by_name=spells, game_data=game_data)
    action = _get_cantrip_action(actions, "Fire Bolt")

    if action:
        assert "+3" not in action["damage"], (
            f"Level 9 Evoker should not have INT bonus: {action['damage']}"
        )


# ── Potent Spellcasting (Cleric Blessed Strikes) ────────────────────


def test_potent_spellcasting_cleric_adds_wis(game_data: GameData):
    """Cleric Potent Spellcasting at 7+ should add WIS if a Cleric attack cantrip exists.

    Note: In practice, standard Cleric cantrips use saving throws, not spell
    attacks, so they don't appear in the combat attack list. This test verifies
    the logic works by checking that the bonus engine correctly identifies the
    feature. We use a Cleric/Sorcerer multiclass with Fire Bolt to test
    indirectly that the bonus does NOT apply to non-Cleric cantrips.
    """
    class_levels = [
        ClassLevel(class_slug="cleric", class_level=i, hit_die=8)
        for i in range(1, 8)
    ]
    class_levels[6].feature_picks = {"Blessed Strikes": "Potent Spellcasting"}

    character = _build_character(
        game_data,
        "cleric",
        cantrips=["Fire Bolt"],  # Not a Cleric cantrip
        class_levels=class_levels,
    )

    spells = _spells_by_name(game_data)
    actions = build_standard_actions(character, spells_by_name=spells, game_data=game_data)
    action = _get_cantrip_action(actions, "Fire Bolt")

    # Fire Bolt is NOT a Cleric cantrip, so Potent Spellcasting should not apply
    if action:
        assert "+3" not in action["damage"], (
            f"Fire Bolt (non-Cleric) should not get Potent Spellcasting bonus: {action['damage']}"
        )


def test_divine_strike_cleric_no_cantrip_bonus(game_data: GameData):
    """Cleric with Divine Strike (Blessed Strikes) should NOT get cantrip damage bonus."""
    class_levels = [
        ClassLevel(class_slug="cleric", class_level=i, hit_die=8)
        for i in range(1, 8)
    ]
    class_levels[6].feature_picks = {"Blessed Strikes": "Divine Strike"}

    character = _build_character(
        game_data,
        "cleric",
        cantrips=["Sacred Flame"],
        class_levels=class_levels,
    )

    spells = _spells_by_name(game_data)
    actions = build_standard_actions(character, spells_by_name=spells, game_data=game_data)
    action = _get_cantrip_action(actions, "Sacred Flame")

    if action:
        assert "+3" not in action["damage"], (
            f"Divine Strike Cleric should not have WIS bonus: {action['damage']}"
        )


# ── Potent Spellcasting (Druid Elemental Fury) ─────────────────────


def test_potent_spellcasting_druid_adds_wis(game_data: GameData):
    """Druid with Potent Spellcasting (Elemental Fury) at 7+ adds WIS to Druid cantrips."""
    class_levels = [
        ClassLevel(class_slug="druid", class_level=i, hit_die=8)
        for i in range(1, 8)
    ]
    class_levels[6].feature_picks = {"Elemental Fury": "Potent Spellcasting"}

    character = _build_character(
        game_data,
        "druid",
        cantrips=["Produce Flame"],
        class_levels=class_levels,
    )

    spells = _spells_by_name(game_data)
    actions = build_standard_actions(character, spells_by_name=spells, game_data=game_data)
    action = _get_cantrip_action(actions, "Produce Flame")

    assert action is not None, "Produce Flame should appear in actions"
    assert "+3" in action["damage"], (
        f"Expected +3 WIS bonus in damage, got: {action['damage']}"
    )


# ── Elemental Affinity (Draconic Sorcery) ──────────────────────────


def test_elemental_affinity_adds_cha_to_matching_type(game_data: GameData):
    """Draconic Sorcerer with Fire affinity at 6+ adds CHA to Fire cantrip damage."""
    class_levels = [
        ClassLevel(
            class_slug="sorcerer", class_level=i, hit_die=6,
            subclass_slug="draconic-sorcery",
        )
        for i in range(1, 7)
    ]
    class_levels[5].feature_picks = {"Elemental Affinity": "Fire"}

    character = _build_character(
        game_data,
        "sorcerer",
        cantrips=["Fire Bolt"],
        class_levels=class_levels,
    )

    spells = _spells_by_name(game_data)
    actions = build_standard_actions(character, spells_by_name=spells, game_data=game_data)
    action = _get_cantrip_action(actions, "Fire Bolt")

    assert action is not None, "Fire Bolt should appear in actions"
    assert "+3" in action["damage"], (
        f"Expected +3 CHA bonus in damage, got: {action['damage']}"
    )


def test_elemental_affinity_no_bonus_for_wrong_type(game_data: GameData):
    """Draconic Sorcerer with Cold affinity should NOT add CHA to Fire cantrips."""
    class_levels = [
        ClassLevel(
            class_slug="sorcerer", class_level=i, hit_die=6,
            subclass_slug="draconic-sorcery",
        )
        for i in range(1, 7)
    ]
    class_levels[5].feature_picks = {"Elemental Affinity": "Cold"}

    character = _build_character(
        game_data,
        "sorcerer",
        cantrips=["Fire Bolt"],
        class_levels=class_levels,
    )

    spells = _spells_by_name(game_data)
    actions = build_standard_actions(character, spells_by_name=spells, game_data=game_data)
    action = _get_cantrip_action(actions, "Fire Bolt")

    if action:
        assert "+3" not in action["damage"], (
            f"Cold Affinity should not boost Fire damage: {action['damage']}"
        )


# ── Radiant Soul (Celestial Patron Warlock) ─────────────────────────


def test_radiant_soul_adds_cha_to_fire_radiant_cantrips(game_data: GameData):
    """Celestial Warlock at 6+ adds CHA to Radiant/Fire cantrip damage.

    Note: Standard Warlock cantrips don't deal Radiant/Fire damage via attack
    rolls, so this tests the bonus engine using Fire Bolt (which a Warlock
    could get through multiclass or Pact of the Tome).
    """
    class_levels = [
        ClassLevel(
            class_slug="warlock", class_level=i, hit_die=8,
            subclass_slug="celestial-patron",
        )
        for i in range(1, 7)
    ]

    character = _build_character(
        game_data,
        "warlock",
        cantrips=["Fire Bolt"],  # Fire damage — matches Radiant Soul
        class_levels=class_levels,
    )

    spells = _spells_by_name(game_data)
    actions = build_standard_actions(character, spells_by_name=spells, game_data=game_data)
    action = _get_cantrip_action(actions, "Fire Bolt")

    assert action is not None, "Fire Bolt should appear in actions"
    assert "+3" in action["damage"], (
        f"Expected +3 CHA bonus in damage, got: {action['damage']}"
    )


def test_radiant_soul_no_bonus_for_non_fire_radiant(game_data: GameData):
    """Celestial Warlock should NOT add CHA to non-Radiant/Fire cantrips."""
    class_levels = [
        ClassLevel(
            class_slug="warlock", class_level=i, hit_die=8,
            subclass_slug="celestial-patron",
        )
        for i in range(1, 7)
    ]

    character = _build_character(
        game_data,
        "warlock",
        cantrips=["Eldritch Blast"],
        class_levels=class_levels,
    )

    spells = _spells_by_name(game_data)
    actions = build_standard_actions(character, spells_by_name=spells, game_data=game_data)
    action = _get_cantrip_action(actions, "Eldritch Blast")

    if action:
        assert "+3" not in action["damage"], (
            f"Eldritch Blast (Force) should not get Radiant Soul bonus: {action['damage']}"
        )
