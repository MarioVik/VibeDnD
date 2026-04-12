Feature: Level-up validation gates (level 1→2)
  Each wizard step validates its required selections before allowing progression.

  Scenario: Class step is valid when leveling the same class
    Given a level-1 Fighter character ready to level up
    Then the class step is valid

  Scenario: Spell step is invalid when required spells not selected
    Given a level-1 Wizard character ready to level up
    When no new spells are selected
    Then the spell step is invalid

  Scenario: Spell step is valid when required spells are selected
    Given a level-1 Wizard character ready to level up
    When the required new spells are selected
    Then the spell step is valid

  Scenario: Choices step is invalid when required choices not selected
    Given a level-1 Warlock character ready to level up
    When no class choices are selected
    Then the choices step is invalid

  Scenario: Choices step is valid when required choices are selected
    Given a level-1 Warlock character ready to level up
    When the required class choices are selected
    Then the choices step is valid
