"""D&D 2024 skill proficiency rules and helpers.

This module is GUI-free and can be imported from anywhere (wizard steps,
character viewer, PDF exporter, etc.).
"""

from __future__ import annotations


def compute_skill_sources(character) -> dict:
    """Return skill grant information derived from the character's choices.

    Returns a dict with:
      "auto"          – list of (skill_name, source_label) tuples for
                        skills granted automatically (background, etc.)
      "class_options" – list of skill names available for class selection
      "choose_count"  – int: how many class skills the player can pick
    """
    auto: list[tuple[str, str]] = []

    # Background skills
    if character.background:
        bg_name = character.background.get("name", "Background")
        for skill in character.background.get("skill_proficiencies", []):
            auto.append((skill, f"Background — {bg_name}"))

    # Subclass grants from level-up (new_proficiencies on ClassLevel)
    for cl in character.class_levels:
        for skill in cl.new_proficiencies:
            auto.append((skill, f"Subclass (level {cl.class_level})"))

    # Class skill choices
    class_options: list[str] = []
    choose_count: int = 0
    if character.character_class:
        skill_choices = character.character_class.get("skill_choices", {})
        choose_count = skill_choices.get("count", 0)
        class_options = list(skill_choices.get("options", []))

    return {
        "auto": auto,
        "class_options": class_options,
        "choose_count": choose_count,
    }
