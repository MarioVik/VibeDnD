"""Central character model for D&D 2024 character creation."""

from dataclasses import dataclass, field
from models.ability_scores import AbilityScores
from models.enums import Ability, Skill, SKILL_BY_NAME


@dataclass
class Character:
    """Holds all character creation choices and computes derived stats."""

    # Identity
    name: str = "New Character"

    # Core choices (stored as parsed data dicts)
    species: dict | None = None
    species_sub_choice: str | None = None
    size_choice: str = "Medium"

    character_class: dict | None = None
    selected_skills: list[str] = field(default_factory=list)

    background: dict | None = None
    ability_bonus_mode: str = "2/1"  # "2/1" or "1/1/1"
    ability_bonus_assignments: dict[str, int] = field(default_factory=dict)

    ability_scores: AbilityScores = field(default_factory=AbilityScores)
    score_method: str = "standard_array"  # "standard_array" or "point_buy"

    feat: dict | None = None                    # Background feat
    species_origin_feat: dict | None = None      # Species origin feat (Human Versatile)
    feat_sub_choices: dict = field(default_factory=dict)

    selected_cantrips: list[str] = field(default_factory=list)
    selected_spells: list[str] = field(default_factory=list)

    equipment_choice_class: str = "A"
    equipment_choice_background: str = "A"

    # Computed properties
    @property
    def level(self) -> int:
        return 1

    @property
    def proficiency_bonus(self) -> int:
        return 2

    @property
    def hit_points(self) -> int:
        if not self.character_class:
            return 0
        hit_die = self.character_class.get("hit_die", 8)
        con_mod = self.ability_scores.modifier("Constitution")
        return max(1, hit_die + con_mod)

    @property
    def armor_class(self) -> int:
        """Unarmored AC = 10 + DEX mod."""
        dex_mod = self.ability_scores.modifier("Dexterity")
        # Special: Barbarian Unarmored Defense = 10 + DEX + CON
        if self.character_class and self.character_class.get("slug") == "barbarian":
            con_mod = self.ability_scores.modifier("Constitution")
            return 10 + dex_mod + con_mod
        # Special: Monk Unarmored Defense = 10 + DEX + WIS
        if self.character_class and self.character_class.get("slug") == "monk":
            wis_mod = self.ability_scores.modifier("Wisdom")
            return 10 + dex_mod + wis_mod
        return 10 + dex_mod

    @property
    def initiative(self) -> int:
        return self.ability_scores.modifier("Dexterity")

    @property
    def speed(self) -> int:
        if self.species:
            return self.species.get("speed", 30)
        return 30

    @property
    def all_skill_proficiencies(self) -> set[str]:
        """All skills the character is proficient in."""
        profs = set()

        # From class
        profs.update(self.selected_skills)

        # From background
        if self.background:
            profs.update(self.background.get("skill_proficiencies", []))

        return profs

    def skill_modifier(self, skill_display_name: str) -> int:
        """Calculate modifier for a skill."""
        skill = SKILL_BY_NAME.get(skill_display_name.lower())
        if not skill:
            return 0
        base_mod = self.ability_scores.modifier(skill.ability.value)
        if skill_display_name in self.all_skill_proficiencies:
            return base_mod + self.proficiency_bonus
        return base_mod

    def skill_modifier_str(self, skill_display_name: str) -> str:
        mod = self.skill_modifier(skill_display_name)
        return f"+{mod}" if mod >= 0 else str(mod)

    def saving_throw_modifier(self, ability_name: str) -> int:
        base = self.ability_scores.modifier(ability_name)
        if self.character_class and ability_name in self.character_class.get("saving_throws", []):
            return base + self.proficiency_bonus
        return base

    def saving_throw_str(self, ability_name: str) -> str:
        mod = self.saving_throw_modifier(ability_name)
        return f"+{mod}" if mod >= 0 else str(mod)

    def is_proficient_save(self, ability_name: str) -> bool:
        if not self.character_class:
            return False
        return ability_name in self.character_class.get("saving_throws", [])

    @property
    def class_name(self) -> str:
        if self.character_class:
            return self.character_class.get("name", "Unknown")
        return "None"

    @property
    def species_name(self) -> str:
        if self.species:
            return self.species.get("name", "Unknown")
        return "None"

    @property
    def background_name(self) -> str:
        if self.background:
            return self.background.get("name", "Unknown")
        return "None"

    @property
    def is_caster(self) -> bool:
        if not self.character_class:
            return False
        return self.character_class.get("caster_type") is not None

    @property
    def cantrips_allowed(self) -> int:
        if not self.character_class:
            return 0
        return self.character_class.get("cantrips_known") or 0

    @property
    def spells_allowed(self) -> int:
        if not self.character_class:
            return 0
        return self.character_class.get("spells_prepared") or 0

    def summary_text(self) -> str:
        """Short one-line summary."""
        parts = []
        if self.species:
            parts.append(self.species_name)
        if self.character_class:
            parts.append(self.class_name)
        return f"Level {self.level} " + " ".join(parts) if parts else "No selections"
