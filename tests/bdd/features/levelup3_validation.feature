Feature: Level-up validation gates (level 2→3)
  Validation at level 3 includes the subclass step which is new.

  Scenario: Class step is valid when leveling the same class at level 3
    Given a level-2 Fighter character ready to level up to 3
    Then the level-3 class step is valid

  Scenario: Subclass step is invalid without selection
    Given a level-2 Fighter character ready to level up to 3
    When no subclass is selected
    Then the subclass step is invalid

  Scenario: Subclass step is valid with selection
    Given a level-2 Fighter character ready to level up to 3
    When a subclass is selected
    Then the subclass step is valid

  Scenario: Spell step is invalid when required spells not selected at level 3
    Given a level-2 Wizard character ready to level up to 3
    When no level-3 spells are selected
    Then the level-3 spell step is invalid

  Scenario: Spell step is valid when required spells selected at level 3
    Given a level-2 Wizard character ready to level up to 3
    When the required level-3 spells are selected
    Then the level-3 spell step is valid
