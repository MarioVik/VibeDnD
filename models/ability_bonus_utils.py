"""Helpers for managing background-based ability score bonuses."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.character import Character


VALID_ABILITY_BONUS_MODES = {"2/1", "1/1/1"}


def get_background_bonus_abilities(character: "Character") -> list[str]:
    """Return the background abilities eligible for origin bonuses."""
    background = character.background or {}
    abilities = background.get("ability_scores", []) or []
    return [ability for ability in abilities if isinstance(ability, str)]


def apply_background_ability_bonuses(character: "Character") -> None:
    """Apply the current background bonus mode and assignments to the model."""
    abilities = get_background_bonus_abilities(character)
    current_bonuses = dict(character.ability_scores.bonuses)

    if character.ability_bonus_mode not in VALID_ABILITY_BONUS_MODES:
        character.ability_bonus_mode = "2/1"

    if not abilities:
        character.ability_bonus_assignments = {}
        character.ability_scores.clear_bonuses()
        return

    saved_assignments = dict(character.ability_bonus_assignments or {})
    mode = character.ability_bonus_mode

    if mode == "2/1":
        plus2 = saved_assignments.get("+2")
        plus1 = saved_assignments.get("+1")

        if plus2 not in abilities:
            plus2 = next(
                (ability for ability in abilities if current_bonuses.get(ability) == 2),
                None,
            )
        if plus2 not in abilities:
            plus2 = abilities[0]

        allowed_plus1 = [ability for ability in abilities if ability != plus2]
        if plus1 not in allowed_plus1:
            plus1 = next(
                (
                    ability
                    for ability in allowed_plus1
                    if current_bonuses.get(ability) == 1
                ),
                None,
            )
        if plus1 not in allowed_plus1:
            plus1 = allowed_plus1[0] if allowed_plus1 else ""

        assignments: dict[str, int | str] = {}
        if plus2:
            assignments["+2"] = plus2
        if plus1:
            assignments["+1"] = plus1
        character.ability_bonus_assignments = assignments
    else:
        character.ability_bonus_assignments = {ability: 1 for ability in abilities}

    character.ability_scores.clear_bonuses()

    if character.ability_bonus_mode == "2/1":
        plus2 = character.ability_bonus_assignments.get("+2", "")
        plus1 = character.ability_bonus_assignments.get("+1", "")
        if plus2:
            character.ability_scores.set_bonus(str(plus2), 2)
        if plus1 and plus1 != plus2:
            character.ability_scores.set_bonus(str(plus1), 1)
    else:
        for ability in abilities:
            character.ability_scores.set_bonus(ability, 1)
