Feature: Level-up apply and persistence (level 1→2)
  After completing the wizard, build_class_level and apply_level_up persist all
  choices to the character model.

  Scenario Outline: Character reaches level 2 after apply
    Given a level-1 <class_name> character ready to level up
    When the level-up is completed with defaults
    Then the character level is 2
    And the character has 2 class levels

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

  Scenario: HP roll is recorded in the new class level
    Given a level-1 Fighter character ready to level up
    When the level-up is completed with defaults
    Then the new class level has a non-null hp_roll

  Scenario: New spells are added to the character after apply
    Given a level-1 Wizard character ready to level up
    When the level-up is completed with a new spell
    Then the character selected spells include the new spell

  Scenario: Class choices are stored in the new class level
    Given a level-1 Warlock character ready to level up
    When the level-up is completed with class choices
    Then the new class level has non-empty new_choices

  Scenario: Ranger languages are added after apply
    Given a level-1 Ranger character ready to level up
    When the level-up is completed with 2 languages
    Then the character chosen languages include the new languages

  Scenario Outline: Level 2 features appear in progression data for the sheet
    Given a level-1 <class_name> character ready to level up
    Then the level 2 progression data has feature_details

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
