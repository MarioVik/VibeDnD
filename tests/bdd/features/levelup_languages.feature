Feature: Level-up language step (level 1→2)
  Ranger gains the Deft Explorer feature at level 2, granting 2 languages.

  Scenario: Ranger has the language step at level 2
    Given a level-1 Ranger character ready to level up
    Then the language step is required

  Scenario: Language step is invalid with fewer than 2 selections
    Given a level-1 Ranger character ready to level up
    When 1 language is selected
    Then the language step is invalid

  Scenario: Language step is valid with exactly 2 selections
    Given a level-1 Ranger character ready to level up
    When 2 languages are selected
    Then the language step is valid

  Scenario Outline: Non-ranger classes do not have the language step
    Given a level-1 <class_name> character ready to level up
    Then the language step is not required

    Examples:
      | class_name |
      | Artificer  |
      | Barbarian  |
      | Fighter    |
      | Wizard     |
