"""Core enumerations for D&D 2024 character creation."""

from enum import Enum


class Ability(Enum):
    STR = "Strength"
    DEX = "Dexterity"
    CON = "Constitution"
    INT = "Intelligence"
    WIS = "Wisdom"
    CHA = "Charisma"


# Mapping from display name to enum
ABILITY_BY_NAME = {a.value.lower(): a for a in Ability}


class Skill(Enum):
    """Each skill maps to (display_name, governing_ability)."""
    ACROBATICS = ("Acrobatics", Ability.DEX)
    ANIMAL_HANDLING = ("Animal Handling", Ability.WIS)
    ARCANA = ("Arcana", Ability.INT)
    ATHLETICS = ("Athletics", Ability.STR)
    DECEPTION = ("Deception", Ability.CHA)
    HISTORY = ("History", Ability.INT)
    INSIGHT = ("Insight", Ability.WIS)
    INTIMIDATION = ("Intimidation", Ability.CHA)
    INVESTIGATION = ("Investigation", Ability.INT)
    MEDICINE = ("Medicine", Ability.WIS)
    NATURE = ("Nature", Ability.INT)
    PERCEPTION = ("Perception", Ability.WIS)
    PERFORMANCE = ("Performance", Ability.CHA)
    PERSUASION = ("Persuasion", Ability.CHA)
    RELIGION = ("Religion", Ability.INT)
    SLEIGHT_OF_HAND = ("Sleight of Hand", Ability.DEX)
    STEALTH = ("Stealth", Ability.DEX)
    SURVIVAL = ("Survival", Ability.WIS)

    @property
    def display_name(self) -> str:
        return self.value[0]

    @property
    def ability(self) -> Ability:
        return self.value[1]


# Mapping from display name to Skill enum
SKILL_BY_NAME = {s.display_name.lower(): s for s in Skill}


ALL_SKILLS = sorted(Skill, key=lambda s: s.display_name)
