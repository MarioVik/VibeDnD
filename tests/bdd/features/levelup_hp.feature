Feature: Level-up HP step (level 1→2)
  Hit points are gained every level. The player chooses average or manual roll.

  Scenario: HP step is valid with average mode
    Given a level-1 Fighter character ready to level up
    When HP mode is set to average
    Then the HP step is valid

  Scenario: HP step is valid with a manual roll of 1
    Given a level-1 Fighter character ready to level up
    When HP mode is set to manual with value 1
    Then the HP step is valid

  Scenario: HP step is invalid with an empty manual roll
    Given a level-1 Fighter character ready to level up
    When HP mode is set to manual with value
    Then the HP step is invalid

  Scenario: HP step is invalid with a manual roll of 0
    Given a level-1 Fighter character ready to level up
    When HP mode is set to manual with value 0
    Then the HP step is invalid

  Scenario: HP step is invalid with a non-numeric manual roll
    Given a level-1 Fighter character ready to level up
    When HP mode is set to manual with value abc
    Then the HP step is invalid

  Scenario Outline: Average HP equals half hit die plus one
    Given a level-1 <class_name> character ready to level up
    Then the average HP gain is <expected_avg>

    Examples:
      | class_name | expected_avg |
      | Barbarian  | 7            |
      | Fighter    | 6            |
      | Ranger     | 6            |
      | Wizard     | 4            |
      | Sorcerer   | 4            |
