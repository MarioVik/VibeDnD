Feature: Level-up subclass selection (level 2→3)
  Every class must select a subclass at level 3. The subclass step validates
  that a selection has been made.

  Scenario Outline: Every class has at least one subclass available
    Given a level-2 <class_name> character ready to level up to 3
    Then at least one subclass is available for <class_name>

    Examples:
      | class_name |
      | Artificer  |
      | Barbarian  |
      | Bard       |
      | Cleric     |
      | Druid      |
      | Fighter    |
      | Monk       |
      | Paladin    |
      | Ranger     |
      | Rogue      |
      | Sorcerer   |
      | Warlock    |
      | Wizard     |

  Scenario: Subclass step is invalid without a selection
    Given a level-2 Fighter character ready to level up to 3
    When no subclass is selected
    Then the subclass step is invalid

  Scenario: Subclass step is valid with a selection
    Given a level-2 Fighter character ready to level up to 3
    When a subclass is selected
    Then the subclass step is valid
