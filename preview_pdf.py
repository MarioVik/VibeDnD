"""Generate a sample PDF character sheet for preview/testing.

Usage:
    python preview_pdf.py [output_path]

Creates a sample D&D character and exports it as a PDF.
Default output: /tmp/vibe_dnd_preview.pdf
"""

import sys
import os

from models.character import Character
from models.ability_scores import AbilityScores
from models.class_level import ClassLevel
from export.pdf_export import export_pdf


def build_sample_character() -> Character:
    """Build a richly populated sample character for PDF preview."""
    char = Character()
    char.name = "Thorn Ironvale"

    # Species
    char.species = {
        "name": "Half-Elf",
        "source": "Player's Handbook",
        "features": [
            {"name": "Darkvision", "description": "You can see in dim light within 60 feet of you as if it were bright light."},
            {"name": "Fey Ancestry", "description": "You have advantage on saving throws against being charmed."},
        ],
    }
    char.size_choice = "Medium"

    # Class
    char.character_class = {
        "name": "Ranger",
        "slug": "ranger",
        "source": "Player's Handbook",
        "hit_die": 10,
        "primary_ability": ["Dexterity", "Wisdom"],
        "saving_throws": ["Strength", "Dexterity"],
        "skill_choices": {"count": 3, "options": ["Animal Handling", "Athletics", "Insight", "Investigation", "Nature", "Perception", "Stealth", "Survival"]},
        "weapon_proficiencies": ["Simple weapons", "Martial weapons"],
        "armor_proficiencies": ["Light armor", "Medium armor", "Shields"],
        "starting_equipment": [
            {"option": "A", "items": "Longbow, 20 Arrows, Quiver, Studded Leather Armor, Explorer's Pack, Druidic Focus, 2 Shortswords"},
            {"option": "B", "items": "150 GP"},
        ],
        "caster_type": "half",
        "spellcasting_ability": "Wisdom",
        "cantrips_known": 0,
        "spells_prepared": 3,
        "spell_slots": {"1st": 2},
    }

    # Skills
    char.selected_skills = ["Perception", "Stealth", "Survival"]

    # Background
    char.background = {
        "name": "Outlander",
        "source": "Player's Handbook",
        "description": "You grew up in the wilds, far from civilization.",
        "features": [
            {"name": "Wanderer", "description": "You have an excellent memory for maps and geography."},
        ],
        "equipment": [
            {"option": "A", "items": "Staff, Hunting Trap, Traveler's Clothes, 10 GP"},
        ],
    }

    # Ability scores
    char.ability_scores = AbilityScores(
        scores={
            "Strength": 12,
            "Dexterity": 15,
            "Constitution": 14,
            "Intelligence": 10,
            "Wisdom": 14,
            "Charisma": 8,
        },
        bonuses={"Dexterity": 1, "Wisdom": 1},
    )
    char.score_method = "standard_array"

    # Background feat
    char.feat = {
        "name": "Alert",
        "source": "Player's Handbook",
        "category": "origin",
        "prerequisites": None,
        "benefits": [
            {"name": "Initiative Proficiency", "description": "You add your Proficiency Bonus to your Initiative rolls."},
            {"name": "Initiative Swap", "description": "Immediately after you roll Initiative, you can swap your Initiative with one willing ally."},
        ],
    }

    # Level progression (level 3 ranger)
    char.class_levels = [
        ClassLevel(class_slug="ranger", class_level=1, hp_roll=None, hit_die=10),
        ClassLevel(class_slug="ranger", class_level=2, hp_roll=7, hit_die=10),
        ClassLevel(
            class_slug="ranger", class_level=3, hp_roll=6, hit_die=10,
            subclass_slug="hunter",
        ),
    ]

    # Spells
    char.selected_spells = ["Cure Wounds", "Hunter S Mark", "Goodberry"]

    # Equipment
    char.equipment_choice_class = "A"
    char.equipment_choice_background = "A"
    char.equipped_weapons = ["Longbow", "Shortsword"]
    char.equipped_armor = ["Studded Leather Armor"]

    # Biography
    char.biography_backstory = (
        "Thorn was raised by a reclusive circle of druids deep in the Whisperwood. "
        "When a blight swept through the forest, destroying everything he knew, "
        "he set out to find its source — and a way to restore the land."
    )
    char.biography_personality = (
        "Quiet and observant, Thorn speaks only when he has something worth saying. "
        "He trusts animals more than people, but is fiercely loyal to those who earn it."
    )
    char.biography_description = (
        "A lean, weathered half-elf with sun-darkened skin and moss-green eyes. "
        "His dark hair is kept short and practical, and faded tattoos of leaves "
        "and vines trace along his forearms."
    )

    return char


def main():
    output = sys.argv[1] if len(sys.argv) > 1 else "/tmp/vibe_dnd_preview.pdf"
    char = build_sample_character()
    export_pdf(char, output)
    print(f"PDF saved to: {output}")


if __name__ == "__main__":
    main()
