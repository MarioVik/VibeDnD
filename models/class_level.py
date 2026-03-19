"""Per-level tracking for character advancement."""

from dataclasses import dataclass, field


@dataclass
class ClassLevel:
    """Represents one level gained in a specific class."""

    class_slug: str = ""         # e.g. "fighter"
    class_level: int = 1         # Level in THIS class (1-20)
    subclass_slug: str | None = None
    feat_choice: str | None = None     # Feat name chosen at ASI levels
    new_cantrips: list[str] = field(default_factory=list)
    new_spells: list[str] = field(default_factory=list)
    swapped_out_cantrip: str | None = None
    swapped_in_cantrip: str | None = None
    swapped_out_spell: str | None = None
    swapped_in_spell: str | None = None
    hp_roll: int | None = None   # HP rolled/chosen for this level (None = level 1 max)
    hit_die: int = 0             # Hit die size for this class (e.g. 10 for d10); 0 = use primary class
    new_choices: list[str] = field(default_factory=list)   # Class choices made at this level (maneuvers, invocations, plans, etc.)
    replaced_choice: str | None = None                     # Existing choice swapped out at this level
    new_proficiencies: list[str] = field(default_factory=list)  # Skill proficiencies gained from subclass
    new_expertise: list[str] = field(default_factory=list)       # Skill expertise gained from subclass
