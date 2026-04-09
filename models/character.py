"""Central character model for D&D 2024 character creation."""

from dataclasses import dataclass, field
from models.ability_scores import AbilityScores
from models.class_level import ClassLevel
from models.enums import Ability, Skill, SKILL_BY_NAME
from models.level1_class_rules import (
    get_effective_armor_proficiencies,
    get_level1_skill_bonus_details,
    get_effective_weapon_proficiencies,
    get_level1_skill_bonus,
)
from models.skill_utils import (
    get_all_skill_advantage_names,
    get_all_skill_expertise_names,
    get_all_skill_proficiency_names,
    get_skill_advantage_source_labels,
    get_skill_expertise_source_labels,
    get_skill_proficiency_source_labels,
)
from models.item_effects import (
    get_ability_check_bonus,
    get_active_ac_bonus,
    get_armor_ac_bonus,
    get_effective_modifier,
    get_save_bonus,
    get_shield_ac_bonus,
    get_unarmored_ac_bonus,
)


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

_ARMOR_STATS = {
    "padded armor": {"base": 11, "dex_cap": None, "shield": False},
    "leather armor": {"base": 11, "dex_cap": None, "shield": False},
    "studded leather armor": {"base": 12, "dex_cap": None, "shield": False},
    "hide armor": {"base": 12, "dex_cap": 2, "shield": False},
    "chain shirt": {"base": 13, "dex_cap": 2, "shield": False},
    "scale mail": {"base": 14, "dex_cap": 2, "shield": False},
    "breastplate": {"base": 14, "dex_cap": 2, "shield": False},
    "half plate armor": {"base": 15, "dex_cap": 2, "shield": False},
    "ring mail": {"base": 14, "dex_cap": 0, "shield": False},
    "chain mail": {"base": 16, "dex_cap": 0, "shield": False},
    "splint armor": {"base": 17, "dex_cap": 0, "shield": False},
    "plate armor": {"base": 18, "dex_cap": 0, "shield": False},
    "shield": {"base": 2, "dex_cap": None, "shield": True},
}


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
    level1_class_choices: dict = field(default_factory=dict)
    spell_grant_choices: dict = field(default_factory=dict)

    selected_cantrips: list[str] = field(default_factory=list)
    selected_spells: list[str] = field(default_factory=list)
    biography_backstory: str = ""
    biography_personality: str = ""
    biography_description: str = ""
    biography_image_data: str = ""
    biography_image_format: str = ""

    equipment_choice_class: str = "A"
    equipment_choice_background: str = "A"
    standard_action_options: dict[str, dict[str, bool]] = field(default_factory=dict)
    attack_order: list[str] = field(default_factory=list)
    equipped_weapons: list[str] | None = None
    equipped_armor: list[str] | None = None
    equipped_gear: list[str] = field(default_factory=list)  # magic gear item keys
    custom_inventory: list[dict] = field(default_factory=list)
    removed_items: dict[str, int] = field(default_factory=dict)
    wealth_adjust_cp: int = 0
    inventory_transactions: list[dict] = field(default_factory=list)
    attuned_items: list[str] = field(default_factory=list)  # item keys

    # Languages
    chosen_languages: list[str] = field(default_factory=list)

    # Level progression
    class_levels: list[ClassLevel] = field(default_factory=list)

    # Mutable HP tracking (persisted)
    current_hit_points: int | None = None  # None means "full" (backward compat)
    temp_hit_points: int = 0
    spent_hit_dice: dict[str, int] = field(default_factory=dict)
    # Maps class_slug -> count spent. e.g. {"fighter": 2, "rogue": 1}

    # Spell slot tracking (persisted)
    used_spell_slots: dict[str, int] = field(default_factory=dict)
    # Maps slot_level -> count spent. e.g. {"1": 2, "2": 0}
    # For Warlocks (Pact Magic), we use "pact" as a prefix or separate key.
    # Actually, let's use "pact" key for pact magic slots.
    used_pact_slots: int = 0
    arcane_recovery_used: bool = False

    @property
    def effective_current_hp(self) -> int:
        """Current HP, defaulting to max if not explicitly set."""
        if self.current_hit_points is not None:
            return self.current_hit_points
        return self.hit_points

    @property
    def hit_dice_pool(self) -> dict[str, tuple[int, int, int]]:
        """Return {class_slug: (remaining, total, die_size)} for each class."""
        totals: dict[str, int] = {}
        for cl in self.class_levels:
            totals[cl.class_slug] = totals.get(cl.class_slug, 0) + 1
        result: dict[str, tuple[int, int, int]] = {}
        for slug, total in totals.items():
            spent = self.spent_hit_dice.get(slug, 0)
            die_size = self._hit_die_for_class(slug)
            result[slug] = (max(0, total - spent), total, die_size)
        return result

    @property
    def total_hit_dice_remaining(self) -> int:
        """Total unspent hit dice across all classes."""
        return sum(rem for rem, _total, _die in self.hit_dice_pool.values())

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
        con_mod = get_effective_modifier(self, "Constitution")

        if not self.class_levels:
            # Legacy: level 1 only
            hit_die = self.character_class.get("hit_die", 8)
            return max(1, hit_die + con_mod)

        total_hp = 0
        for cl in self.class_levels:
            hit_die = self._hit_die_for_class(cl.class_slug)
            if cl.class_level == 1 and cl == self.class_levels[0]:
                # First level ever: max hit die + CON (or manual override)
                if cl.hp_roll is not None:
                    total_hp += cl.hp_roll + con_mod
                else:
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
        """Compute AC including magic item bonuses."""
        dex_mod = get_effective_modifier(self, "Dexterity")

        # Unarmored baseline (including class features)
        unarmored_ac = 10 + dex_mod
        if self.character_class and self.character_class.get("slug") == "barbarian":
            con_mod = get_effective_modifier(self, "Constitution")
            unarmored_ac = 10 + dex_mod + con_mod
        if self.character_class and self.character_class.get("slug") == "monk":
            wis_mod = get_effective_modifier(self, "Wisdom")
            unarmored_ac = 10 + dex_mod + wis_mod

        # General AC bonus (Ring of Protection, etc.)
        general_bonus = get_active_ac_bonus(self)

        equipped = set((self.equipped_armor or []))
        if not equipped:
            unarmored_bonus = get_unarmored_ac_bonus(self)
            return unarmored_ac + general_bonus + unarmored_bonus

        # Build variant → base armor mapping from custom inventory
        variant_base: dict[str, str] = {}
        for ent in getattr(self, "custom_inventory", []) or []:
            if str(ent.get("category", "")) != "Armor":
                continue
            variant = ent.get("variant")
            if variant:
                key = str(ent.get("name", "")).strip().lower()
                variant_base[key] = variant.strip().lower()

        shield_bonus = 0
        has_body_armor = False
        body_ac_options = []
        for armor_name in equipped:
            base_name = variant_base.get(armor_name, armor_name)
            stats = _ARMOR_STATS.get(base_name)
            if not stats:
                continue
            if stats.get("shield"):
                shield_bonus = 2 + get_shield_ac_bonus(self, armor_name)
                continue
            has_body_armor = True
            cap = stats.get("dex_cap")
            dex_part = dex_mod if cap is None else min(dex_mod, cap)
            magic_armor_bonus = get_armor_ac_bonus(self, armor_name)
            body_ac_options.append(stats.get("base", 10) + dex_part + magic_armor_bonus)

        if body_ac_options:
            return max(body_ac_options) + shield_bonus + general_bonus

        # No body armor but has shield — add unarmored bonus
        if not has_body_armor:
            unarmored_bonus = get_unarmored_ac_bonus(self)
            return unarmored_ac + shield_bonus + general_bonus + unarmored_bonus

        return unarmored_ac + shield_bonus + general_bonus

    @property
    def initiative(self) -> int:
        return get_effective_modifier(self, "Dexterity")

    @property
    def speed(self) -> int:
        if self.species:
            return self.species.get("speed", 30)
        return 30

    @property
    def all_skill_proficiencies(self) -> set[str]:
        """All skills the character is proficient in."""
        return get_all_skill_proficiency_names(self)

    @property
    def all_skill_expertise(self) -> set[str]:
        """All skills the character has expertise in."""
        return get_all_skill_expertise_names(self)

    @property
    def all_skill_advantages(self) -> set[str]:
        """All skills the character has advantage on from permanent sources."""
        return get_all_skill_advantage_names(self)

    def skill_modifier(self, skill_display_name: str) -> int:
        """Calculate modifier for a skill."""
        skill = SKILL_BY_NAME.get(skill_display_name.lower())
        if not skill:
            return 0
        base_mod = get_effective_modifier(self, skill.ability.value)
        check_bonus = get_ability_check_bonus(self)
        if skill_display_name in self.all_skill_expertise:
            return (
                base_mod
                + (self.proficiency_bonus * 2)
                + get_level1_skill_bonus(self, skill_display_name)
                + check_bonus
            )
        if skill_display_name in self.all_skill_proficiencies:
            return (
                base_mod
                + self.proficiency_bonus
                + get_level1_skill_bonus(self, skill_display_name)
                + check_bonus
            )
        return base_mod + get_level1_skill_bonus(self, skill_display_name) + check_bonus

    def skill_modifier_str(self, skill_display_name: str) -> str:
        mod = self.skill_modifier(skill_display_name)
        return f"+{mod}" if mod >= 0 else str(mod)

    def skill_modifier_breakdown(self, skill_display_name: str) -> dict:
        """Return a structured breakdown of how a skill modifier is calculated."""
        skill = SKILL_BY_NAME.get(skill_display_name.lower())
        if not skill:
            return {
                "skill_name": skill_display_name,
                "ability_name": "",
                "components": [],
                "total": 0,
            }

        ability_name = skill.ability.value
        components = [
            {
                "label": f"{ability_name} modifier",
                "value": get_effective_modifier(self, ability_name),
                "sources": [],
            }
        ]

        if skill_display_name in self.all_skill_proficiencies:
            components.append(
                {
                    "label": "Proficiency bonus",
                    "value": self.proficiency_bonus,
                    "sources": get_skill_proficiency_source_labels(
                        self, skill_display_name
                    ),
                }
            )

        if skill_display_name in self.all_skill_expertise:
            components.append(
                {
                    "label": "Expertise bonus",
                    "value": self.proficiency_bonus,
                    "sources": get_skill_expertise_source_labels(
                        self, skill_display_name
                    ),
                }
            )

        for bonus in get_level1_skill_bonus_details(self, skill_display_name):
            components.append(
                {
                    "label": str(bonus.get("label", "") or "Other bonus"),
                    "value": int(bonus.get("value", 0) or 0),
                    "sources": [],
                }
            )

        check_bonus = get_ability_check_bonus(self)
        if check_bonus:
            components.append(
                {
                    "label": "Item bonus (ability checks)",
                    "value": check_bonus,
                    "sources": [],
                }
            )

        return {
            "skill_name": skill_display_name,
            "ability_name": ability_name,
            "components": components,
            "total": self.skill_modifier(skill_display_name),
        }

    def skill_modifier_breakdown_text(self, skill_display_name: str) -> str:
        """Return a compact tooltip-friendly breakdown of a skill modifier."""
        breakdown = self.skill_modifier_breakdown(skill_display_name)
        components = breakdown.get("components", [])
        if not components:
            return skill_display_name

        def _fmt(value: int) -> str:
            return f"+{value}" if value >= 0 else str(value)

        lines = [
            str(breakdown.get("skill_name", skill_display_name) or skill_display_name)
        ]
        for component in components:
            line = f"{component['label']}: {_fmt(int(component['value']))}"
            sources = [
                str(source).strip()
                for source in component.get("sources", [])
                if str(source).strip()
            ]
            if sources:
                line += f" ({', '.join(sources)})"
            lines.append(line)
        lines.append(f"Total: {_fmt(int(breakdown.get('total', 0) or 0))}")

        # Append advantage info if applicable
        adv_sources = get_skill_advantage_source_labels(self, skill_display_name)
        if adv_sources:
            lines.append(f"\u2605 Advantage ({', '.join(adv_sources)})")

        return "\n".join(lines)

    def saving_throw_modifier(self, ability_name: str) -> int:
        base = get_effective_modifier(self, ability_name)
        item_bonus = get_save_bonus(self)
        if self.character_class and ability_name in self.character_class.get(
            "saving_throws", []
        ):
            return base + self.proficiency_bonus + item_bonus
        return base + item_bonus

    def saving_throw_str(self, ability_name: str) -> str:
        mod = self.saving_throw_modifier(ability_name)
        return f"+{mod}" if mod >= 0 else str(mod)

    def is_proficient_save(self, ability_name: str) -> bool:
        if not self.character_class:
            return False
        return ability_name in self.character_class.get("saving_throws", [])

    @property
    def effective_weapon_proficiencies(self) -> list[str]:
        """Weapon proficiencies after level-1 class choices are applied."""
        return get_effective_weapon_proficiencies(self)

    @property
    def effective_armor_proficiencies(self) -> list[str]:
        """Armor proficiencies after level-1 class choices are applied."""
        return get_effective_armor_proficiencies(self)

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

    # Spell Slot Management
    def use_spell_slot(self, level: str):
        """Consume a spell slot of the given level ('1'-'9' or 'pact')."""
        if level == "pact":
            self.used_pact_slots += 1
        else:
            self.used_spell_slots[level] = self.used_spell_slots.get(level, 0) + 1

    def recover_spell_slots(self, level: str, count: int):
        """Recover spent spell slots."""
        if level == "pact":
            self.used_pact_slots = max(0, self.used_pact_slots - count)
        else:
            current = self.used_spell_slots.get(level, 0)
            self.used_spell_slots[level] = max(0, current - count)

    def reset_spell_slots(self):
        """Fully restore all spell slots (e.g. Long Rest)."""
        self.used_spell_slots.clear()
        self.used_pact_slots = 0
