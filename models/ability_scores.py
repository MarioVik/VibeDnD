"""Ability score assignment: standard array and point buy."""

from dataclasses import dataclass, field
from models.enums import Ability


STANDARD_ARRAY = [15, 14, 13, 12, 10, 8]

POINT_BUY_COSTS = {8: 0, 9: 1, 10: 2, 11: 3, 12: 4, 13: 5, 14: 7, 15: 9}
POINT_BUY_BUDGET = 27
POINT_BUY_MIN = 8
POINT_BUY_MAX = 15


@dataclass
class AbilityScores:
    """Stores base ability scores and background bonuses."""
    scores: dict[str, int] = field(default_factory=lambda: {
        "Strength": 10, "Dexterity": 10, "Constitution": 10,
        "Intelligence": 10, "Wisdom": 10, "Charisma": 10,
    })
    bonuses: dict[str, int] = field(default_factory=dict)

    def base(self, ability_name: str) -> int:
        return self.scores.get(ability_name, 10)

    def bonus(self, ability_name: str) -> int:
        return self.bonuses.get(ability_name, 0)

    def total(self, ability_name: str) -> int:
        return self.base(ability_name) + self.bonus(ability_name)

    def modifier(self, ability_name: str) -> int:
        return (self.total(ability_name) - 10) // 2

    def modifier_str(self, ability_name: str) -> str:
        mod = self.modifier(ability_name)
        return f"+{mod}" if mod >= 0 else str(mod)

    def set_base(self, ability_name: str, value: int):
        self.scores[ability_name] = value

    def set_bonus(self, ability_name: str, value: int):
        self.bonuses[ability_name] = value

    def clear_bonuses(self):
        self.bonuses.clear()

    def point_buy_total(self) -> int:
        """Calculate total points spent under point buy rules."""
        total = 0
        for score in self.scores.values():
            total += POINT_BUY_COSTS.get(score, 0)
        return total

    def point_buy_remaining(self) -> int:
        return POINT_BUY_BUDGET - self.point_buy_total()

    def is_valid_point_buy(self) -> bool:
        total = self.point_buy_total()
        if total > POINT_BUY_BUDGET:
            return False
        for score in self.scores.values():
            if score < POINT_BUY_MIN or score > POINT_BUY_MAX:
                return False
        return True

    def is_valid_standard_array(self) -> bool:
        used = sorted(self.scores.values(), reverse=True)
        return used == sorted(STANDARD_ARRAY, reverse=True)
