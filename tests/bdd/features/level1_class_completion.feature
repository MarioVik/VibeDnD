Feature: Level 1 class creation completion
  Character creation should not complete until every level 1 class-granted
  choice that affects creation has been resolved.

  Scenario Outline: Missing a required level 1 choice blocks completion
    Given a fully completed level 1 <class_slug> character
    When the <requirement_id> requirement is removed from that character
    Then the <requirement_id> blocker is reported for that character

    Examples:
      | class_slug | requirement_id      |
      | artificer  | class-cantrips      |
      | barbarian  | weapon-mastery      |
      | bard       | class-cantrips      |
      | cleric     | divine-order        |
      | druid      | primal-order        |
      | fighter    | fighting-style      |
      | monk       | class-equipment     |
      | paladin    | weapon-mastery      |
      | ranger     | weapon-mastery      |
      | rogue      | rogue-expertise     |
      | sorcerer   | class-cantrips      |
      | warlock    | warlock-invocation  |
      | wizard     | class-cantrips      |

  Scenario Outline: Completed level 1 characters satisfy the rules
    Given a fully completed level 1 <class_slug> character
    Then the character has no unmet level 1 requirements

    Examples:
      | class_slug |
      | artificer  |
      | barbarian  |
      | bard       |
      | cleric     |
      | druid      |
      | fighter    |
      | monk       |
      | paladin    |
      | ranger     |
      | rogue      |
      | sorcerer   |
      | warlock    |
      | wizard     |
