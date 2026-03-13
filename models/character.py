"""Central character model for D&D 2024 character creation."""

from dataclasses import dataclass, field
from models.ability_scores import AbilityScores
from models.class_level import ClassLevel
from models.enums import Ability, Skill, SKILL_BY_NAME


# D&D 2024 multiclass prerequisites: 13+ in the class's primary ability
_MULTICLASS_PREREQUISITES = {
    "barbarian": ["Strength"],
    "bard": ["Charisma"],
    "cleric": ["Wisdom"],
    "druid": ["Wisdom"],
    "fighter": ["Strength", "Dexterity"],  # 13 in STR or DEX
    "monk": ["Dexterity", "Wisdom"],  # 13 in DEX and WIS
    "paladin": ["Strength", "Charisma"],  # 13 in STR and CHA
    "ranger": ["Dexterity", "Wisdom"],  # 13 in DEX and WIS
    "rogue": ["Dexterity"],
    "sorcerer": ["Charisma"],
    "warlock": ["Charisma"],
    "wizard": ["Intelligence"],
    "artificer": ["Intelligence"],
}

# Classes that need only ONE of the listed abilities at 13+
_MULTICLASS_OR_CLASSES = {"fighter"}


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

    feat: dict | None = None  # Background feat
    species_origin_feat: dict | None = None  # Species origin feat (Human Versatile)
    feat_sub_choices: dict = field(default_factory=dict)

    selected_cantrips: list[str] = field(default_factory=list)
    selected_spells: list[str] = field(default_factory=list)

    equipment_choice_class: str = "A"
    equipment_choice_background: str = "A"
    standard_action_options: dict[str, dict[str, bool]] = field(default_factory=dict)

    # Level progression
    class_levels: list[ClassLevel] = field(default_factory=list)

    # Computed properties
    @property
    def level(self) -> int:
        """Total character level (sum of all class levels)."""
        if not self.class_levels:
            return 1
        return len(self.class_levels)

    @property
    def proficiency_bonus(self) -> int:
        return (self.level - 1) // 4 + 2

    @property
    def hit_points(self) -> int:
        if not self.character_class:
            return 0
        con_mod = self.ability_scores.modifier("Constitution")

        if not self.class_levels:
            # Legacy: level 1 only
            hit_die = self.character_class.get("hit_die", 8)
            return max(1, hit_die + con_mod)

        total_hp = 0
        for cl in self.class_levels:
            hit_die = self._hit_die_for_class(cl.class_slug)
            if cl.class_level == 1 and cl == self.class_levels[0]:
                # First level ever: max hit die + CON
                total_hp += hit_die + con_mod
            elif cl.hp_roll is not None:
                total_hp += cl.hp_roll + con_mod
            else:
                # Default: average (rounded up)
                total_hp += (hit_die // 2 + 1) + con_mod
        return max(1, total_hp)

    def _hit_die_for_class(self, class_slug: str) -> int:
        """Get hit die size for a class slug."""
        # Primary class data dict
        if self.character_class and self.character_class.get("slug") == class_slug:
            return self.character_class.get("hit_die", 8)
        # Check stored hit_die on class_levels (set during level-up)
        for cl in self.class_levels:
            if cl.class_slug == class_slug and cl.hit_die > 0:
                return cl.hit_die
        return 8

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
        if self.character_class and ability_name in self.character_class.get(
            "saving_throws", []
        ):
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

    @property
    def current_subclass(self) -> str | None:
        """Get the subclass slug for the primary class, if any."""
        if not self.class_levels:
            return None
        primary = self.class_levels[0].class_slug if self.class_levels else ""
        return self.subclass_for_class(primary)

    def subclass_for_class(self, class_slug: str) -> str | None:
        """Get the subclass slug for a specific class, if any."""
        for cl in self.class_levels:
            if cl.class_slug == class_slug and cl.subclass_slug:
                return cl.subclass_slug
        return None

    def class_level_in(self, class_slug: str) -> int:
        """Get the number of levels in a specific class."""
        return sum(1 for cl in self.class_levels if cl.class_slug == class_slug)

    @property
    def is_multiclass(self) -> bool:
        """Check if character has levels in multiple classes."""
        if not self.class_levels:
            return False
        slugs = {cl.class_slug for cl in self.class_levels}
        return len(slugs) > 1

    def multiclass_prereqs_met(self, class_slug: str) -> tuple[bool, str]:
        """Check if the character meets multiclass prerequisites for a class.

        Returns (met, reason) where reason explains what's missing.
        """
        reqs = _MULTICLASS_PREREQUISITES.get(class_slug, [])
        if not reqs:
            return True, ""

        scores = []
        for ability_name in reqs:
            score = self.ability_scores.total(ability_name)
            scores.append((ability_name, score))

        if class_slug in _MULTICLASS_OR_CLASSES:
            # Need at least ONE at 13+
            if any(s >= 13 for _, s in scores):
                return True, ""
            names = " or ".join(a for a, _ in scores)
            return False, f"Requires {names} 13+"
        else:
            # Need ALL at 13+
            missing = [a for a, s in scores if s < 13]
            if not missing:
                return True, ""
            return False, f"Requires {', '.join(missing)} 13+"

    def summary_text(self) -> str:
        """Short one-line summary."""
        parts = []
        if self.species:
            parts.append(self.species_name)
        if self.character_class:
            parts.append(self.class_name)
        if self.is_multiclass:
            # Show multiclass breakdown
            from collections import Counter

            counts = Counter(cl.class_slug for cl in self.class_levels)
            mc_parts = [f"{slug.title()} {n}" for slug, n in counts.items()]
            return f"Level {self.level} {self.species_name} ({'/'.join(mc_parts)})"
        return f"Level {self.level} " + " ".join(parts) if parts else "No selections"
