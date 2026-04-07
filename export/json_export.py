"""Export character as JSON."""

import json
from models.character import Character
from models.enums import ALL_SKILLS
from models.item_effects import get_effective_ability_score, get_effective_modifier


def character_to_dict(character: Character) -> dict:
    """Serialize character to a dictionary."""
    c = character
    abilities = {}
    for name in [
        "Strength",
        "Dexterity",
        "Constitution",
        "Intelligence",
        "Wisdom",
        "Charisma",
    ]:
        abilities[name] = {
            "base": c.ability_scores.base(name),
            "bonus": c.ability_scores.bonus(name),
            "total": get_effective_ability_score(c, name),
            "modifier": get_effective_modifier(c, name),
        }

    saves = {}
    for name in [
        "Strength",
        "Dexterity",
        "Constitution",
        "Intelligence",
        "Wisdom",
        "Charisma",
    ]:
        saves[name] = {
            "modifier": c.saving_throw_modifier(name),
            "proficient": c.is_proficient_save(name),
        }

    skills = {}
    for skill in ALL_SKILLS:
        skills[skill.display_name] = {
            "modifier": c.skill_modifier(skill.display_name),
            "proficient": skill.display_name in c.all_skill_proficiencies,
            "expertise": skill.display_name in c.all_skill_expertise,
            "ability": skill.ability.value,
        }

    return {
        "name": c.name,
        "level": c.level,
        "species": c.species_name,
        "species_sub_choice": c.species_sub_choice,
        "size": c.size_choice,
        "class": c.class_name,
        "background": c.background_name,
        "hit_points": c.hit_points,
        "armor_class": c.armor_class,
        "speed": c.speed,
        "initiative": c.initiative,
        "proficiency_bonus": c.proficiency_bonus,
        "abilities": abilities,
        "saving_throws": saves,
        "skills": skills,
        "skill_proficiencies": sorted(list(c.all_skill_proficiencies)),
        "skill_expertise": sorted(list(c.all_skill_expertise)),
        "background_feat": c.background.get("feat") if c.background else None,
        "species_origin_feat": c.species_origin_feat.get("name")
        if c.species_origin_feat
        else None,
        "level1_class_choices": dict(getattr(c, "level1_class_choices", {}) or {}),
        "cantrips": c.selected_cantrips,
        "spells": c.selected_spells,
        "biography_backstory": getattr(c, "biography_backstory", ""),
        "biography_personality": getattr(c, "biography_personality", ""),
        "biography_description": getattr(c, "biography_description", ""),
        "biography_image_data": getattr(c, "biography_image_data", ""),
        "biography_image_format": getattr(c, "biography_image_format", ""),
        "equipment_choice_class": c.equipment_choice_class,
        "equipment_choice_background": c.equipment_choice_background,
        "score_method": c.score_method,
    }


def export_json(character: Character, path: str):
    """Save character as JSON file."""
    data = character_to_dict(character)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
