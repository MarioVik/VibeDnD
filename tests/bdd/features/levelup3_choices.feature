Feature: Level-up class choices (level 2→3)
  Some subclasses gain class-specific choices at level 3. These are subclass-
  dependent, not base-class features.

  Scenario: Battle Master gains 3 maneuvers at level 3
    Given a level-2 Fighter character ready to level up to 3
    And the Battle Master subclass is selected
    Then the subclass class choices gain count at level 3 is 3
    And the subclass class choice options are not empty

  Scenario: Arcane Archer gains 2 arcane shots at level 3
    Given a level-2 Fighter character ready to level up to 3
    And the Arcane Archer subclass is selected
    Then the subclass class choices gain count at level 3 is 2

  Scenario: Tattooed Warrior gains 2 tattoos at level 3
    Given a level-2 Monk character ready to level up to 3
    And the Tattooed Warrior subclass is selected
    Then the subclass class choices gain count at level 3 is 2

  Scenario: Hunter gains 1 feature option at level 3
    Given a level-2 Ranger character ready to level up to 3
    And the Hunter subclass is selected
    Then the subclass class choices gain count at level 3 is 1

  Scenario: Champion Fighter has no class choices at level 3
    Given a level-2 Fighter character ready to level up to 3
    And the Champion subclass is selected
    Then no subclass class choices config exists at level 3
