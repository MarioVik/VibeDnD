Feature: Level-up spell deltas (level 1→2)
  Casters gain new prepared spells and/or cantrips at level 2.

  Scenario Outline: Spell deltas are correct at level 2
    Given a level-1 <class_name> character ready to level up
    Then the new cantrip count is <new_cantrips>
    And the new prepared spell count is <new_prepared>

    Examples:
      | class_name | new_cantrips | new_prepared |
      | Artificer  | 0            | 1            |
      | Barbarian  | 0            | 0            |
      | Bard       | 0            | 1            |
      | Cleric     | 0            | 1            |
      | Druid      | 0            | 1            |
      | Fighter    | 0            | 0            |
      | Monk       | 0            | 0            |
      | Paladin    | 0            | 1            |
      | Ranger     | 0            | 1            |
      | Rogue      | 0            | 0            |
      | Sorcerer   | 0            | 2            |
      | Warlock    | 0            | 1            |
      | Wizard     | 0            | 1            |

  Scenario Outline: Spell summary lines are produced for casters
    Given a level-1 <class_name> character ready to level up
    Then the spell summary is not empty

    Examples:
      | class_name |
      | Artificer  |
      | Bard       |
      | Cleric     |
      | Druid      |
      | Paladin    |
      | Ranger     |
      | Sorcerer   |
      | Warlock    |
      | Wizard     |

  Scenario Outline: Non-casters produce no spell summary
    Given a level-1 <class_name> character ready to level up
    Then the spell summary is empty

    Examples:
      | class_name |
      | Barbarian  |
      | Fighter    |
      | Monk       |
      | Rogue      |
