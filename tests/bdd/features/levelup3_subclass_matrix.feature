Feature: Exhaustive subclass verification at level 3
  Every subclass that comes online at level 3 must have complete feature data,
  allow any required subclass choices to be made, and surface those features
  and choices in the shared character sheet data.

  Scenario: Every level-3 subclass feature is stored and displayed
    Given the full level-3 subclass matrix
    When each subclass is applied at level 3 with valid defaults
    Then the matrix contains 93 level-3 subclasses
    And every subclass has level-3 features with names and descriptions
    And every subclass level-up records its subclass slug
    And every level-3 subclass feature appears in the shared character sheet subclass section

  Scenario: Every level-3 subclass choice can be selected and displayed
    Given the full level-3 subclass matrix
    When each subclass with level-3 choices is applied using valid subclass choices
    Then exactly 4 subclasses grant level-3 class choices
    And every level-3 subclass choice config can satisfy its required picks
    And every selected level-3 subclass choice is persisted on the class level
    And every selected level-3 subclass choice appears in the shared character sheet history
