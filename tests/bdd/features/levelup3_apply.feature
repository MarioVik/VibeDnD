Feature: Level-up apply and persistence (level 2→3)
  After completing level 3, all choices are persisted including the subclass.

  Scenario Outline: Character reaches level 3 after apply
    Given a level-2 <class_name> character ready to level up to 3
    When the level-3 up is completed with defaults
    Then the character level is 3
    And the character has 3 class levels

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

  Scenario: Subclass slug is recorded in the new class level
    Given a level-2 Fighter character ready to level up to 3
    When the level-3 up is completed with defaults
    Then the level-3 class level has a subclass slug

  Scenario: HP roll is recorded at level 3
    Given a level-2 Fighter character ready to level up to 3
    When the level-3 up is completed with defaults
    Then the level-3 class level has a non-null hp_roll

  Scenario: New spells are added after level 3 apply
    Given a level-2 Wizard character ready to level up to 3
    When the level-3 up is completed with a new spell
    Then the character selected spells include the level-3 new spell

  Scenario: Subclass choices are stored after level 3 apply
    Given a level-2 Fighter character ready to level up to 3
    And the Battle Master subclass is selected
    When the level-3 up is completed with subclass choices
    Then the level-3 class level has non-empty new_choices

  Scenario Outline: Level 3 features appear in progression data
    Given a level-2 <class_name> character ready to level up to 3
    Then the level 3 progression data has feature_details

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
