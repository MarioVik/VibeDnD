Feature: Level-up spell deltas (level 2→3)
  Casters gain new prepared spells at level 3. No class gains new cantrips.

  Scenario Outline: Spell deltas are correct at level 3
    Given a level-2 <class_name> character ready to level up to 3
    Then the level-3 new cantrip count is <new_cantrips>
    And the level-3 new prepared spell count is <new_prepared>

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
