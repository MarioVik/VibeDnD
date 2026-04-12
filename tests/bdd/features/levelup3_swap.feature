Feature: Level-up spell swap (level 2→3)
  Bard, Sorcerer, and Warlock can swap spells at level 3 if they have existing
  selections.

  Scenario Outline: Swap-eligible classes can swap at level 3
    Given a level-2 <class_name> character ready to level up to 3
    And the level-3 character has existing spells
    Then level-3 spell swap is available

    Examples:
      | class_name |
      | Bard       |
      | Sorcerer   |
      | Warlock    |

  Scenario Outline: Non-swap classes cannot swap at level 3
    Given a level-2 <class_name> character ready to level up to 3
    Then level-3 spell swap is not available

    Examples:
      | class_name |
      | Artificer  |
      | Barbarian  |
      | Cleric     |
      | Druid      |
      | Fighter    |
      | Monk       |
      | Paladin    |
      | Ranger     |
      | Rogue      |
      | Wizard     |
