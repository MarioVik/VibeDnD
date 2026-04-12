Feature: Level-up class choices (level 1→2)
  Some classes gain class-specific choices at level 2 (plans, metamagic,
  invocations). These appear on the Class Choices step.

  Scenario Outline: Classes with choices at level 2 have the right gain count
    Given a level-1 <class_name> character ready to level up
    Then the class choices gain count at level 2 is <expected_gains>

    Examples:
      | class_name | expected_gains |
      | Artificer  | 4              |
      | Sorcerer   | 2              |
      | Warlock    | 2              |

  Scenario Outline: Available options are non-empty for classes with choices
    Given a level-1 <class_name> character ready to level up
    Then the available class choice options are not empty

    Examples:
      | class_name |
      | Artificer  |
      | Sorcerer   |
      | Warlock    |

  Scenario Outline: Classes without choices at level 2 have no config
    Given a level-1 <class_name> character ready to level up
    Then no class choices config exists

    Examples:
      | class_name |
      | Barbarian  |
      | Bard       |
      | Cleric     |
      | Druid      |
      | Fighter    |
      | Monk       |
      | Paladin    |
      | Ranger     |
      | Rogue      |
      | Wizard     |
